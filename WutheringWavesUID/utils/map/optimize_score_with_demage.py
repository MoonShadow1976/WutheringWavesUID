import copy
import json
import logging
import math
from pathlib import Path
import sys

from msgspec import json as msgjson

logging.disable(logging.CRITICAL + 1)  # 禁用所有级别（包括 CRITICAL）
# 将项目根目录加入 sys.path
root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root))

from WutheringWavesUID.utils.api.model import RoleDetailData
from WutheringWavesUID.utils.ascension.weapon import get_weapon_model
from WutheringWavesUID.utils.calc import WuWaCalc
from WutheringWavesUID.utils.damage.abstract import DamageDetailRegister, DamageRankRegister
from WutheringWavesUID.utils.damage.register_char import register_char
from WutheringWavesUID.utils.damage.register_echo import register_echo
from WutheringWavesUID.utils.damage.register_sonata import register_sonata
from WutheringWavesUID.utils.damage.register_weapon import register_weapon
from WutheringWavesUID.utils.expression_evaluator import find_first_matching_expression
from WutheringWavesUID.utils.map.damage.register import register_damage, register_rank
from WutheringWavesUID.utils.resource.constant import ID_FULL_CHAR_NAME

SCRIPT_PATH = Path(__file__).parents[0]
MAP_PATH = SCRIPT_PATH / "character"
DETAIL_PATH = SCRIPT_PATH / "detail_json"
CHAR_DETAIL_PATH = DETAIL_PATH / "char"
WEAPON_DETAIL_PATH = DETAIL_PATH / "weapon"
SONATA_DETAIL_PATH = DETAIL_PATH / "sonata"

LIMIT_ROLE = SCRIPT_PATH / "1.json"
LIMIT_DATA_PATH = SCRIPT_PATH / "limit.json"
TEMPLATE_DATA_PATH = SCRIPT_PATH / "templata.json"
ID_NAME_PATH = SCRIPT_PATH / "id2name.json"

limit_data = json.loads(LIMIT_DATA_PATH.read_text(encoding="utf-8"))
template_data = json.loads(TEMPLATE_DATA_PATH.read_text(encoding="utf-8"))
id2Name = json.loads(ID_NAME_PATH.read_text(encoding="utf-8"))
limit_role = json.loads(LIMIT_ROLE.read_text(encoding="utf-8"))
limit_role_id_list = {i["role"]["roleId"]: i for i in limit_role}

# ----- 声骸副词条离散值（仅用于取值） -----
phantom_sub_value = [
    {"name": "攻击", "values": ["30", "40", "50", "60"]},
    {"name": "攻击%", "values": ["6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%"]},
    {"name": "生命", "values": ["320", "360", "390", "430", "470", "510", "540", "580"]},
    {"name": "生命%", "values": ["6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%"]},
    {"name": "防御", "values": ["40", "50", "60", "70"]},
    {"name": "防御%", "values": ["8.1%", "9%", "10%", "10.9%", "11.8%", "12.8%", "13.8%", "14.7%"]},
    {"name": "暴击", "values": ["6.3%", "6.9%", "7.5%", "8.1%", "8.7%", "9.3%", "9.9%", "10.5%"]},
    {"name": "暴击伤害", "values": ["12.6%", "13.8%", "15%", "16.2%", "17.4%", "18.6%", "19.8%", "21.0%"]},
    {"name": "普攻伤害加成", "values": ["6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%"]},
    {"name": "重击伤害加成", "values": ["6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%"]},
    {"name": "共鸣技能伤害加成", "values": ["6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%"]},
    {"name": "共鸣解放伤害加成", "values": ["6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%"]},
    {"name": "技能伤害加成", "values": ["6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%"]},
    {"name": "共鸣效率", "values": ["6.8%", "7.6%", "8.4%", "9.2%", "10%", "10.8%", "11.6%", "12.4%"]},
]
phantom_sub_value_map = {i["name"]: i["values"] for i in phantom_sub_value}

# ----- 声骸主词条离散值（仅用于构建基准面板） -----
phantom_main_value = [
    {"name": "攻击", "values": ["0", "100", "150"]},
    {"name": "攻击%", "values": ["18%", "30%", "33%"]},
    {"name": "生命", "values": ["2280", "0", "0"]},
    {"name": "生命%", "values": ["22.8%", "30%", "33%"]},
    {"name": "防御%", "values": ["18%", "38%", "41.8%"]},
    {"name": "暴击", "values": ["0%", "0%", "22%"]},
    {"name": "暴击伤害", "values": ["0%", "0%", "44%"]},
    {"name": "共鸣效率", "values": ["0%", "32%", "0%"]},
    {"name": "属性伤害加成", "values": ["0%", "30%", "0%"]},
    {"name": "治疗效果加成", "values": ["0%", "0%", "26.4%"]},
]
phantom_main_value_map = {i["name"]: i["values"] for i in phantom_main_value}

# 四种伤害加成顺序（用于 skill_weight）
JINENG_LIST = [
    "普攻伤害加成",
    "重击伤害加成",
    "共鸣技能伤害加成",
    "共鸣解放伤害加成",
]

# ----- 声骸副词条概率表 -----
phantom_sub_prob = {
    "攻击": {"30": 0.067961, "40": 0.524272, "50": 0.378641, "60": 0.029126},
    "防御": {"40": 0.145631, "50": 0.446602, "60": 0.320388, "70": 0.087379},
    "暴击": {
        "6.3%": 0.233333,
        "6.9%": 0.233333,
        "7.5%": 0.233333,
        "8.1%": 0.08,
        "8.7%": 0.08,
        "9.3%": 0.08,
        "9.9%": 0.03,
        "10.5%": 0.03,
    },
    "暴击伤害": {
        "12.6%": 0.233333,
        "13.8%": 0.233333,
        "15%": 0.233333,
        "16.2%": 0.08,
        "17.4%": 0.08,
        "18.6%": 0.08,
        "19.8%": 0.03,
        "21.0%": 0.03,
    },
    "生命": {
        "320": 0.067961,
        "360": 0.077670,
        "390": 0.203883,
        "430": 0.242718,
        "470": 0.174757,
        "510": 0.145631,
        "540": 0.058252,
        "580": 0.029126,
    },
    "生命%": {
        "6.4%": 0.067961,
        "7.1%": 0.077670,
        "7.9%": 0.203883,
        "8.6%": 0.242718,
        "9.4%": 0.174757,
        "10.1%": 0.145631,
        "10.9%": 0.058252,
        "11.6%": 0.029126,
    },
    "防御%": {
        "8.1%": 0.067961,
        "9%": 0.077670,
        "10%": 0.203883,
        "10.9%": 0.242718,
        "11.8%": 0.174757,
        "12.8%": 0.145631,
        "13.8%": 0.058252,
        "14.7%": 0.029126,
    },
    "共鸣效率": {
        "6.8%": 0.067961,
        "7.6%": 0.077670,
        "8.4%": 0.203883,
        "9.2%": 0.242718,
        "10%": 0.174757,
        "10.8%": 0.145631,
        "11.6%": 0.058252,
        "12.4%": 0.029126,
    },
    "攻击%": {
        "6.4%": 0.067961,
        "7.1%": 0.077670,
        "7.9%": 0.203883,
        "8.6%": 0.242718,
        "9.4%": 0.174757,
        "10.1%": 0.145631,
        "10.9%": 0.058252,
        "11.6%": 0.029126,
    },
    # 伤害加成概率与攻击%一致
    "普攻伤害加成": {
        "6.4%": 0.067961,
        "7.1%": 0.077670,
        "7.9%": 0.203883,
        "8.6%": 0.242718,
        "9.4%": 0.174757,
        "10.1%": 0.145631,
        "10.9%": 0.058252,
        "11.6%": 0.029126,
    },
    "重击伤害加成": {
        "6.4%": 0.067961,
        "7.1%": 0.077670,
        "7.9%": 0.203883,
        "8.6%": 0.242718,
        "9.4%": 0.174757,
        "10.1%": 0.145631,
        "10.9%": 0.058252,
        "11.6%": 0.029126,
    },
    "共鸣技能伤害加成": {
        "6.4%": 0.067961,
        "7.1%": 0.077670,
        "7.9%": 0.203883,
        "8.6%": 0.242718,
        "9.4%": 0.174757,
        "10.1%": 0.145631,
        "10.9%": 0.058252,
        "11.6%": 0.029126,
    },
    "共鸣解放伤害加成": {
        "6.4%": 0.067961,
        "7.1%": 0.077670,
        "7.9%": 0.203883,
        "8.6%": 0.242718,
        "9.4%": 0.174757,
        "10.1%": 0.145631,
        "10.9%": 0.058252,
        "11.6%": 0.029126,
    },
    "技能伤害加成": {
        "6.4%": 0.067961,
        "7.1%": 0.077670,
        "7.9%": 0.203883,
        "8.6%": 0.242718,
        "9.4%": 0.174757,
        "10.1%": 0.145631,
        "10.9%": 0.058252,
        "11.6%": 0.029126,
    },
}


def calc_sub_max_score(_temp, sub_props, jineng: list | None = None, skill_weight: list | None = None):
    score = 0
    jineng_list = [
        "普攻伤害加成",
        "重击伤害加成",
        "共鸣技能伤害加成",
        "共鸣解放伤害加成",
    ]
    for i in _temp:
        ratio = 1
        if jineng is not None and i == "技能伤害加成":
            ratio = jineng
        elif i in jineng_list:
            if skill_weight is not None:
                ratio = skill_weight[jineng_list.index(i)]
        _phantom_value = phantom_sub_value_map[i][-1]
        if "%" in _phantom_value:
            _phantom_value = _phantom_value.replace("%", "")
        _phantom_value = float(_phantom_value)
        score += sub_props[i] * _phantom_value * ratio
    return math.floor(score * 1000) / 1000


def get_calc_map(ctx: dict, char_name: str, char_id: int | str):
    """匹配角色目录下的条件 json，返回最终的 calc 数据（用于伤害计算）"""
    if str(char_id) in ID_FULL_CHAR_NAME:
        char_name = ID_FULL_CHAR_NAME[str(char_id)]
    char_path = MAP_PATH / char_name
    if not char_path.is_dir():
        char_path = MAP_PATH / "default"

    def check_conditions(file_name):
        condition_path = char_path / file_name
        if condition_path.exists():
            with open(condition_path, encoding="utf-8") as f:
                expressions = msgjson.decode(f.read())
            return find_first_matching_expression(ctx, expressions)
        return None

    calc_json_path = check_conditions("condition-user.json") or check_conditions("condition.json") or "calc.json"
    # 条件命中的文件缺失时回退到默认 calc.json
    if not (char_path / calc_json_path).exists():
        calc_json_path = "calc.json"
    with open(char_path / calc_json_path, encoding="utf-8") as f:
        return msgjson.decode(f.read())


def build_base_data(char_id, weapon_id, max_sub_props, chain_num: int | None = None):
    """构建基准面板（空词条-精1-指定共鸣链），用于计算基础伤害

    chain_num 为 None 时保持旧行为：五星 0 链，四星 6 链。
    """
    # 深拷贝，避免不同共鸣链之间互相污染 limit_role_id_list 里的缓存数据
    base_data = copy.deepcopy(limit_role_id_list.get(int(char_id), {}))
    base_phantom = None
    if not base_data:
        return None, None

    # 共鸣链
    if chain_num is not None:
        for i in base_data["chainList"]:
            i["unlocked"] = i.get("order", 0) <= chain_num
        print(f"{base_data['role']['roleName']} 共鸣链设置为 {chain_num}链")
    elif base_data["role"]["starLevel"] == 5:
        for i in base_data["chainList"]:
            i["unlocked"] = False
        print(f"{base_data['role']['roleName']} 共鸣链设置为 0链")

    # 精1
    base_data["weaponData"]["resonLevel"] = 1
    print(f"{base_data['role']['roleName']} 武器设置为 精1")

    # 声骸词条
    for i in base_data["phantomData"]["equipPhantomList"]:
        for j in i["subProps"]:
            j["attributeValue"] = phantom_sub_value_map[j["attributeName"]][0]
    # base_phantom = copy.deepcopy(base_data["phantomData"])

    use_crit = False
    weapon = get_weapon_model(weapon_id)
    if weapon:
        for key in weapon.get_max_level_stat_tuple():
            if key[0] == "暴击伤害":
                use_crit = True
                break

    for i, echo in enumerate(base_data["phantomData"]["equipPhantomList"]):
        # echo["mainProps"] = []
        if i == 0:
            main_key_4 = "暴击" if use_crit else "暴击伤害"
            echo["cost"] = 4
            echo["mainProps"] = [
                {"attributeName": main_key_4, "attributeValue": phantom_main_value_map[main_key_4][2]},
                {"attributeName": "攻击", "attributeValue": phantom_main_value_map["攻击"][2]},
            ]
        elif i == 1:
            main_key_3_1 = f"{base_data['role']['attributeName']}伤害加成"
            echo["cost"] = 3
            echo["mainProps"] = [
                {"attributeName": main_key_3_1, "attributeValue": phantom_main_value_map["属性伤害加成"][1]},
                {"attributeName": "攻击", "attributeValue": phantom_main_value_map["攻击"][1]},
            ]
        elif i == 2:
            main_key_3_2 = "攻击%"
            if "生命" in max_sub_props:
                main_key_3_2 = "生命%"
            elif "防御" in max_sub_props:
                main_key_3_2 = "防御%"
            elif "共鸣效率" in max_sub_props:
                main_key_3_2 = "共鸣效率"
            echo["cost"] = 3
            echo["mainProps"] = [
                {"attributeName": main_key_3_2, "attributeValue": phantom_main_value_map["属性伤害加成"][1]},
                {"attributeName": "攻击", "attributeValue": phantom_main_value_map["攻击"][1]},
            ]
        elif i == 3 or i == 4:
            main_key_1 = "攻击%"
            if "生命" in max_sub_props:
                main_key_1 = "生命%"
            elif "防御" in max_sub_props:
                main_key_1 = "防御%"
            echo["cost"] = 1
            echo["mainProps"] = [
                {"attributeName": main_key_1, "attributeValue": phantom_main_value_map[main_key_1][0]},
                {"attributeName": "生命", "attributeValue": phantom_main_value_map["生命"][0]},
            ]
        echo["subProps"] = []
    print(
        f"{base_data['role']['roleName']} 声骸副词条设置为 空，主词条设置为 4/3/3/1/1 {main_key_4} {main_key_3_1} {main_key_3_2} {main_key_1} {main_key_1}\n"
    )

    return base_data, base_phantom


def save_calc_json(char_name, data, file_name: str = "calc.json"):
    """保存更新后的 calc 文件（file_name 缺省为 calc.json）"""
    char_dir = MAP_PATH / char_name
    char_dir.mkdir(parents=True, exist_ok=True)
    file_path = char_dir / file_name
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return file_path


def calc_weights(char_name, char_id, calc_data, weapon_id, chain_num: int | None = None):
    """核心：按指定共鸣链，用「满值副词条带来的伤害提升」重新拟合 calc_data 的权重。

    只计算不落盘：成功时就地更新并返回 calc_data，失败返回 None。
    chain_num 决定基准面板解锁几条共鸣链（None = 旧行为：五星 0 链 / 四星 6 链）。
    """
    max_sub_props = calc_data["max_sub_props"]
    skill_weight = calc_data["skill_weight"]

    # 构建基准面板
    base_data, _base_phantom = build_base_data(char_id, weapon_id, max_sub_props, chain_num)
    if not base_data:
        print(f"角色{char_name}({char_id})未适配极限面板，跳过更新权重")
        return None

    # 获取伤害计算类
    rankDetail = DamageRankRegister.find_class(str(char_id))
    damageDetail = DamageDetailRegister.find_class(str(char_id))
    if not rankDetail or not damageDetail:
        print(f"角色{char_name}({char_id})未适配伤害计算，跳过更新权重")
        return None

    # 计算排行伤害还是总伤害
    all_damage = True

    # 辅助函数：计算伤害
    def calc_damage(role_dict, need_crit=False, all_damage=False):
        role_obj = RoleDetailData(**role_dict)
        calc = WuWaCalc(role_obj)
        calc.phantom_pre = calc.prepare_phantom()
        calc.phantom_card = calc.enhance_summation_phantom_value(calc.phantom_pre)
        calc.calc_temp = get_calc_map(
            calc.phantom_card,
            role_obj.role.roleName,
            role_obj.role.roleId,
        )
        calc.role_card = calc.enhance_summation_card_value(calc.phantom_card)
        attr = calc.card_sort_map_to_attribute(calc.role_card)

        if all_damage:
            crit_damage, expected_damage = 0, 0
            for _dindex, damage_temp in enumerate(damageDetail):
                # if "/" in damage_temp["title"]:
                # print(f"        总伤害统计跳过组队伤害：{damage_temp['title']}")
                # continue
                attr_temp = copy.deepcopy(attr)
                cd, ed = damage_temp["func"](attr_temp, role_obj)
                crit_damage += int(cd.replace(",", "")[:6])
                expected_damage += int(ed.replace(",", "")[:6])
        else:
            cd, ed = rankDetail["func"](attr, role_obj)
            crit_damage = int(cd.replace(",", ""))
            expected_damage = int(ed.replace(",", ""))

        print(
            f"  角色面板 暴击：{attr.crit_rate} 爆伤：{attr.crit_dmg} 攻击：{attr.effect_attack} 防御：{attr.effect_def} 生命：{attr.effect_life} 加成：{attr.dmg_bonus} 共效：{attr.energy_regen}"
        )
        if need_crit:
            return crit_damage
        return expected_damage

    base_crit_damage = calc_damage(base_data, True, all_damage=all_damage)
    base_expected_damage = calc_damage(base_data, all_damage=all_damage)

    # print(f"基础词条：test {base_data['phantomData']['equipPhantomList'][0]}=> 空")
    print(f"基础伤害(只取前三位有效数字) 暴击：{base_crit_damage} 期望伤害：{base_expected_damage}\n")
    # print(f"测试词条：test {base_phantom['equipPhantomList'][0]}")
    # 对每个 max_sub_props 词条，在第一个声骸添加该词条（最大值），计算提升
    improvements = {}
    for sub_name in max_sub_props:
        if "伤害加成" in sub_name:
            jineng_index = skill_weight.index(max(skill_weight))
            sub_name = JINENG_LIST[jineng_index]

        values = phantom_sub_value_map[sub_name]
        if not values:
            continue
        max_val_str = values[-1]

        test_data = copy.deepcopy(base_data)
        # test_data["phantomData"] = copy.deepcopy(base_phantom)
        # for i in test_data["phantomData"]["equipPhantomList"]:
        # for j in i["subProps"]:
        #     if j["attributeName"] == sub_name.replace("%", ""):
        #         j["attributeValue"] = max_val_str
        #         break
        # i["subProps"].append(
        test_data["phantomData"]["equipPhantomList"][0]["subProps"].append(
            {
                "attributeName": sub_name.replace("%", ""),
                "attributeValue": max_val_str,
            }
        )

        # if "暴击" != sub_name.replace("%", ""):
        #     need_crit = True
        #     base_damage = base_crit_damage
        # else:
        need_crit = False
        base_damage = base_expected_damage
        new_damage = calc_damage(test_data, need_crit, all_damage=all_damage)
        improvement = (new_damage - base_damage) / base_damage
        improvement = improvement / float(max_val_str.replace("%", ""))
        improvements[sub_name] = improvement
        print(f"满值 {sub_name}({max_val_str})\t 测试伤害：{new_damage}/{base_damage}\t 每点词条数值提升：{improvement}")
        # print(f"测试词条：test {test_data['phantomData']['equipPhantomList'][0]}")

    # ========== 使用 sub_max=65 归一化 ==========
    jineng = max(skill_weight)

    # 构建未缩放的权重（improvements 是每点词条数值的伤害提升）
    new_sub_props_uns = {}
    for sub_name, imp in improvements.items():
        if "伤害加成" in sub_name:
            key = "技能伤害加成"
        else:
            key = sub_name
        new_sub_props_uns[key] = imp

    current_sub_max = calc_sub_max_score(max_sub_props, new_sub_props_uns, jineng, skill_weight)
    print(f"当前未缩放权重下的 sub_max: {current_sub_max}")

    scale = 65.0 / current_sub_max if current_sub_max != 0 else 1.0
    print(f"缩放因子: {scale}")

    new_sub_props = {k: math.floor(v * scale * 100000) / 100000 for k, v in new_sub_props_uns.items()}
    print(f"\n计算得到的权重表：{new_sub_props}")

    # 更新 calc_data
    for k, v in new_sub_props.items():
        if "伤害加成" in k:
            k = "技能伤害加成"
        calc_data["sub_props"][k] = v

    return calc_data


def update_calc_json_weights(char_name, char_id, calc_file, weapon_id, chain_num=None, out_file=None):
    """读取 calc 文件，按 chain_num 重新计算权重并写盘（out_file 缺省时覆盖原文件）"""
    calc_path = MAP_PATH / char_name / calc_file
    if not calc_path.exists():
        print(f"未找到 {calc_path}，跳过更新")
        return None

    with open(calc_path, encoding="utf-8") as f:
        calc_data = json.load(f)

    new_data = calc_weights(char_name, char_id, calc_data, weapon_id, chain_num)
    if new_data is None:
        return None

    save_path = save_calc_json(char_name, new_data, out_file or calc_file)
    print(f"已更新权重表: {save_path}")
    return new_data


def register_all():
    """注册伤害计算所需的武器/声骸/伤害/排行/角色数据"""
    register_weapon()
    register_echo()
    register_sonata()
    register_damage()
    register_rank()
    register_char()


if __name__ == "__main__":
    register_all()

    for char_limit in limit_data["charList"]:
        char_name = char_limit["name"]
        for i in ["心"]:
            if i == char_name:
                print(f"\n角色{char_name} 开始计算")
                update_calc_json_weights(char_name, char_limit["charId"], char_limit["calcFile"], char_limit["weaponId"])
