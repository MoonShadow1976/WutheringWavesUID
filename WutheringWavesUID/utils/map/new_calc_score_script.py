"""按共鸣链（0~6）批量生成角色声骸评分权重

直接运行：
    python WutheringWavesUID/utils/map/new_calc_score_script.py

对 TARGET_CHARS 命中的每个角色依次执行：
    1. 复制 calc.json 的「通用权重」作为模板，逐个链数调用
       optimize_score_with_demage.calc_weights()：把基准面板的共鸣链换成该链数，
       用「满值副词条带来的伤害提升」重新拟合 sub_props 权重（归一化到 sub_max = 65）；
    2. 权重完全相同的链数合并成一组，共用同一个权重文件（0 链和 1 链这种情况就不再重复出文件）：
           含 0 链的组 -> calc.json
           其余        -> calc-{链数}链.json
       例如：
           {0, 1}    -> calc.json
           {2}       -> calc-2链.json
           {4, 5, 6} -> calc-4-6链.json
           {2, 4}    -> calc-2+4链.json（不连续时用 + 连接）
    3. 删掉该角色目录下上一次生成、这次已经被合并掉的 calc-*链.json；
    4. 重写角色的 condition.json —— 链数规则排在最前，原有条件（套装等）顺延。
       WuWaCalc 已把共鸣链数量写进条件匹配上下文（key = "chain"），
       所以打分时会自动挑到对应链数的权重文件；
    5. 全部生成完后调用 calc_score_script.read_calc_json_files()，
       统一重算 score_max / props_grade 并重建 1.json，得到最终权重。
"""

import copy
import json
from pathlib import Path
import re
import sys

SCRIPT_PATH = Path(__file__).parents[0]
MAP_PATH = SCRIPT_PATH / "character"
LIMIT_DATA_PATH = SCRIPT_PATH / "limit.json"

# 把插件根目录加入 sys.path，和 optimize_score_with_demage 使用同样的绝对导入
ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from WutheringWavesUID.utils.map.calc_score_script import read_calc_json_files
from WutheringWavesUID.utils.map.optimize_score_with_demage import (
    calc_weights,
    register_all,
    save_calc_json,
)

limit_data = json.loads(LIMIT_DATA_PATH.read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

# 目标角色（按名称包含匹配，和 limit.json 里的 name 比较）
TARGET_CHARS = ["心", "锁暝"]

# 需要生成权重的共鸣链数量
CHAIN_LIST = [0, 1, 2, 3, 4, 5, 6]

# 通用权重模板：每个链数都以它的结构为底复制
BASE_CALC_FILE = "calc.json"

# 是否重写 condition.json（链数规则插到最前，保留原有条件）
WRITE_CONDITION = True

# 生成结束后是否统一重算 score_max / props_grade 并重建 1.json
FINALIZE_SCORE = True

# 本脚本生成的权重文件长这样：calc-1链.json / calc-4-6链.json / calc-2+4链.json
# 只清理匹配这个格式的文件，calc-新光套.json 这类手工文件不会被误删
CHAIN_FILE_PATTERN = re.compile(r"^calc-[\d\-+]+链\.json$")

# 两组权重的最大相对差异小于这个比例时，认为它们是同一条权重，合并共用一个文件。
# 权重本身被 floor 到 1e-5，有些链数之间只差最后一个最小位（伤害计算里的浮点噪声，
# 比如全队统一的伤害乘区不改变相对收益），这种差异对评分的影响远小于 3%。
WEIGHT_TOLERANCE = 3e-2


def chains_tag(chains: list[int]) -> str:
    """{2} -> '2'；{4, 5, 6} -> '4-6'；{2, 4} -> '2+4'"""
    if len(chains) == 1:
        return str(chains[0])
    if chains == list(range(chains[0], chains[-1] + 1)):
        return f"{chains[0]}-{chains[-1]}"
    return "+".join(str(chain) for chain in chains)


def weights_diff(a: dict, b: dict) -> float:
    """两份权重表的最大相对差异，用来判断能不能共用同一个文件"""
    diff = 0.0
    for key in set(a) | set(b):
        va, vb = a.get(key, 0.0), b.get(key, 0.0)
        diff = max(diff, abs(va - vb) / max(1e-9, abs(va), abs(vb)))
    return diff


def group_chains(chain_data: dict[int, dict]) -> list[list[int]]:
    """把权重相同的相邻链数并成一组，共用同一个权重文件

    每次都拿组内第一条链做基准（而不是上一条），避免误差逐级累积后把差距明显的链也并进来。
    """
    groups: list[list[int]] = []
    for chain in sorted(chain_data):
        if groups:
            base = groups[-1][0]
            diff = weights_diff(chain_data[base]["sub_props"], chain_data[chain]["sub_props"])
            if diff <= WEIGHT_TOLERANCE:
                print(f"[合组] {chain}链 与 {base}链 权重最大差异 {diff:.2e}，共用文件")
                groups[-1].append(chain)
                continue
        groups.append([chain])
    return groups


def group_calc_file(chains: list[int]) -> str:
    """含 0 链的组沿用 calc.json（条件不匹配时的默认回退），其余按链数命名"""
    if chains[0] == 0:
        return BASE_CALC_FILE
    return f"calc-{chains_tag(chains)}链.json"


def build_condition_expressions(char_dir: Path, chain_files: dict[int, str]) -> list[dict]:
    """链数规则在前（大链优先），原有非链数条件顺延保留"""
    condition_path = char_dir / "condition.json"
    old_expressions: list[dict] = []
    if condition_path.exists():
        old_expressions = json.loads(condition_path.read_text(encoding="utf-8")) or []

    # 旧的链数规则由本次重新生成，直接丢掉；其余条件（套装等）原样保留
    kept = [expr for expr in old_expressions if expr.get("key") != "chain"]

    chain_rules = [
        {"choose": chain_files[chain], "key": "chain", "op": "=", "value": chain} for chain in sorted(chain_files, reverse=True)
    ]
    return chain_rules + kept


def remove_stale_chain_files(char_dir: Path, keep: set[str]) -> None:
    """删掉上一次生成、这次已经合并掉的 calc-*链.json"""
    for path in char_dir.glob("calc-*链.json"):
        if CHAIN_FILE_PATTERN.match(path.name) and path.name not in keep:
            path.unlink()
            print(f"[清理] 删除已合并的旧权重文件 {path.name}")


def generate_char(char_limit: dict) -> dict[int, str]:
    """生成单个角色各共鸣链的权重文件，返回 {链数: 文件名}"""
    char_name = char_limit["name"]
    char_id = char_limit["charId"]
    weapon_id = char_limit["weaponId"]
    char_dir = MAP_PATH / char_name
    base_path = char_dir / BASE_CALC_FILE

    if not base_path.exists():
        print(f"[跳过] {char_name} 没有 {BASE_CALC_FILE}")
        return {}

    # 复制通用权重，作为所有链数的模板
    base_data = json.loads(base_path.read_text(encoding="utf-8"))

    # 1) 先算出每个链数的权重，这一步还不落盘
    chain_data: dict[int, dict] = {}
    for chain in CHAIN_LIST:
        print(f"\n===== {char_name} {chain}链 =====")
        calc_data = copy.deepcopy(base_data)
        new_data = calc_weights(char_name, char_id, calc_data, weapon_id, chain)
        if new_data is None:
            print(f"[失败] {char_name} {chain}链 权重计算失败，跳过")
            continue
        chain_data[chain] = new_data

    if not chain_data:
        return {}

    # 2) 权重相同的链数合并，共用一个文件
    chain_files: dict[int, str] = {}
    for group in group_chains(chain_data):
        file_name = group_calc_file(group)
        tag = chains_tag(group)
        print(f"[合并] {char_name} {tag}链 -> {file_name}")

        data = copy.deepcopy(chain_data[group[0]])
        data["name"] = f"{char_name}-{tag}链"
        save_calc_json(char_name, data, file_name)

        for chain in group:
            chain_files[chain] = file_name

    # 3) 清理上次遗留、这次已合并掉的文件
    remove_stale_chain_files(char_dir, set(chain_files.values()))

    # 有 calc.json 之外的权重文件时才需要写条件（0 链是条件不匹配时的默认回退）
    if WRITE_CONDITION and any(file_name != BASE_CALC_FILE for file_name in chain_files.values()):
        expressions = build_condition_expressions(char_dir, chain_files)
        condition_path = char_dir / "condition.json"
        condition_path.write_text(json.dumps(expressions, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[条件] 已重写 {condition_path}（{len(expressions)} 条规则）")

    return chain_files


def main():
    register_all()

    summary: dict[str, dict[int, str]] = {}
    for char_limit in limit_data["charList"]:
        char_name = char_limit["name"]
        for i in TARGET_CHARS:
            if i == char_name:
                print(f"\n########## 角色{char_name} 开始生成 {min(CHAIN_LIST)}~{max(CHAIN_LIST)} 链权重 ##########")
                summary[char_name] = generate_char(char_limit)
                break

    if not summary:
        print(f"没有命中任何目标角色：{TARGET_CHARS}")
        return

    if FINALIZE_SCORE:
        print("\n########## 统一重算 score_max / props_grade 并重建 1.json ##########")
        read_calc_json_files(MAP_PATH)

    print("\n########## 生成结果 ##########")
    for char_name, files in summary.items():
        merged: dict[str, list[int]] = {}
        for chain, file_name in files.items():
            merged.setdefault(file_name, []).append(chain)
        print(f"{char_name}:")
        for file_name, chains in merged.items():
            print(f"    {file_name:<18} <- {chains_tag(sorted(chains))}链")


if __name__ == "__main__":
    main()
