import copy
from pathlib import Path

from gsuid_core.logger import logger
from msgspec import json as msgjson

from ..ascension.constant import fixed_name, sum_percentages
from ..resource.constant import SKILL_TREE_BREACH_MAP
from .model import CharacterModel

MAP_PATH = Path(__file__).parent.parent / "map/detail_json/char"
char_id_data = {}


def read_char_json_files(directory):
    files = directory.rglob("*.json")

    for file in files:
        try:
            with open(file, encoding="utf-8") as f:
                data = msgjson.decode(f.read())
                file_name = file.name.split(".")[0]
                char_id_data[file_name] = data
        except Exception as e:
            logger.exception(f"read_char_json_files load fail decoding {file}", e)


read_char_json_files(MAP_PATH)


class WavesCharResult:
    def __init__(self):
        self.name = ""
        self.starLevel = 4
        self.stats = {"life": 0.0, "atk": 0.0, "def": 0.0}
        self.skillTrees = {}
        self.fixed_skill = {}


def get_breach(breach: int | None, level: int):
    if breach is None:
        if level <= 20:
            breach = 0
        elif level <= 40:
            breach = 1
        elif level <= 50:
            breach = 2
        elif level <= 60:
            breach = 3
        elif level <= 70:
            breach = 4
        elif level <= 80:
            breach = 5
        elif level <= 90:
            breach = 6
        else:
            breach = 0

    return breach


def extract_param_index(desc: str, search_text: str) -> int | None:
    """提取描述中search_text后面的第一个占位符索引"""
    if (start := desc.find(search_text)) == -1:
        return None
    if (brace_start := desc.find("{", start)) == -1:
        return None
    if (brace_end := desc.find("}", brace_start)) == -1:
        return None
    try:
        return int(desc[brace_start + 1 : brace_end])
    except ValueError:
        return None


def get_char_detail(char_id: str | int, level: int, breach: int | None = None) -> WavesCharResult:
    """
    breach 突破
    resonLevel 精炼
    """
    result = WavesCharResult()
    if str(char_id) not in char_id_data:
        logger.exception(f"get_char_detail char_id: {char_id} not found")
        return result

    breach = get_breach(breach, level)

    char_data = char_id_data[str(char_id)]
    result.name = char_data["name"]
    result.starLevel = char_data["starLevel"]
    result.stats = copy.deepcopy(char_data["stats"][str(breach)][str(level)])
    result.skillTrees = char_data["skillTree"]

    # 构建skill_tree列表
    skill_tree = []
    for threshold, keys in SKILL_TREE_BREACH_MAP.items():
        if breach >= threshold:
            skill_tree.extend(char_data["skillTree"][key] for key in keys if key in char_data["skillTree"])

    for value in skill_tree:
        skill_info = value.get("skill", {})
        name, desc, params = skill_info.get("name", ""), skill_info.get("desc", ""), skill_info.get("param", [])

        search_text = None
        if name in fixed_name:
            search_text = name
        elif skill_info.get("type") == "固有技能":
            for fixed_skill_name in fixed_name:
                if desc.startswith(fixed_skill_name) or desc.startswith(f"{char_data['name']}的{fixed_skill_name}"):
                    search_text = fixed_skill_name
                    break
        if not search_text:
            continue

        logger.debug(f"get_char_detail search_text: {search_text}, name: {name}")
        if (index := extract_param_index(desc, search_text)) is not None and index < len(params):
            clean_name = search_text.replace("提升", "").replace("全", "")
            if clean_name not in result.fixed_skill:
                result.fixed_skill[clean_name] = "0%"
            result.fixed_skill[clean_name] = sum_percentages(params[index], result.fixed_skill[clean_name])
            logger.debug(f"get_char_detail {search_text}: {params[index]}")

    return result


def get_char_detail2(role) -> WavesCharResult:
    role_id = role.role.roleId
    role_level = role.role.level
    role_breach = role.role.breach
    return get_char_detail(role_id, role_level, role_breach)


def get_char_id(char_name):
    return next((_id for _id, value in char_id_data.items() if value["name"] == char_name), None)


def get_char_model(char_id: str | int) -> CharacterModel | None:
    if str(char_id) not in char_id_data:
        return None
    return CharacterModel(**char_id_data[str(char_id)])


class CharExp:
    """角色经验计算器"""

    # 角色升级所需经验 {等级: 经验值}
    LEVEL_COST: dict[str, int] = {
        "1": 400,
        "2": 400,
        "3": 500,
        "4": 600,
        "5": 700,
        "6": 900,
        "7": 1000,
        "8": 1200,
        "9": 1300,
        "10": 1500,
        "11": 1700,
        "12": 2000,
        "13": 2200,
        "14": 2400,
        "15": 2700,
        "16": 3000,
        "17": 3300,
        "18": 3600,
        "19": 3900,
        "20": 4300,
        "21": 4600,
        "22": 5000,
        "23": 5400,
        "24": 5800,
        "25": 6300,
        "26": 6700,
        "27": 7200,
        "28": 7700,
        "29": 8200,
        "30": 8700,
        "31": 9300,
        "32": 9800,
        "33": 10400,
        "34": 11000,
        "35": 11700,
        "36": 12300,
        "37": 13000,
        "38": 13700,
        "39": 14400,
        "40": 15100,
        "41": 15900,
        "42": 16700,
        "43": 17500,
        "44": 18300,
        "45": 19200,
        "46": 20000,
        "47": 20900,
        "48": 21900,
        "49": 22800,
        "50": 23800,
        "51": 24800,
        "52": 25800,
        "53": 26900,
        "54": 28000,
        "55": 29100,
        "56": 30300,
        "57": 31400,
        "58": 32600,
        "59": 33900,
        "60": 35100,
        "61": 36400,
        "62": 37700,
        "63": 39100,
        "64": 40500,
        "65": 41900,
        "66": 43300,
        "67": 44800,
        "68": 46300,
        "69": 47900,
        "70": 49500,
        "71": 51100,
        "72": 52800,
        "73": 54500,
        "74": 56200,
        "75": 58000,
        "76": 59800,
        "77": 61600,
        "78": 63500,
        "79": 65400,
        "80": 67400,
        "81": 69400,
        "82": 71400,
        "83": 73500,
        "84": 75600,
        "85": 77800,
        "86": 80000,
        "87": 82300,
        "88": 84600,
        "89": 86900,
        "90": 105600,
        "91": 107400,
        "92": 110000,
        "93": 113600,
        "94": 118600,
        "95": 125500,
        "96": 134900,
        "97": 147300,
        "98": 163600,
        "99": 184500,
        "100": 0,
    }

    # 角色经验瓶配置：经验值 -> {id, cost}
    EXP_ITEM: dict[int, dict[str, int]] = {
        1000: {"id": 43010001, "cost": 350},
        3000: {"id": 43010002, "cost": 1050},
        8000: {"id": 43010003, "cost": 2800},
        20000: {"id": 43010004, "cost": 7000},
    }

    @classmethod
    def get_level_up_exp(cls, head_level: int | str, tail_level: int | str) -> int:
        """计算从 head_level 升到 tail_level 所需总经验"""
        total = 0
        for level in range(int(head_level), int(tail_level)):
            total += cls.LEVEL_COST.get(str(level), 0)
        return total

    @classmethod
    def get_cost_from_exp(cls, total_exp: int) -> list[dict[str, int]]:
        """
        根据总经验值返回所需经验瓶列表（按优先级：金瓶 > 紫瓶 > 蓝瓶 > 绿瓶），
        绿瓶允许溢出。最后附加一个汇总条目 {"id": 2, "num": 总cost}。
        """
        exp_values = sorted(cls.EXP_ITEM.keys(), reverse=True)
        min_exp_value = exp_values[-1]
        normal_exp_values = exp_values[:-1]  # 除最低级外的其他瓶子

        result = []
        total_cost = 0

        for exp in normal_exp_values:
            count = total_exp // exp
            if count > 0:
                total_exp %= exp
                result.append({"id": cls.EXP_ITEM[exp]["id"], "num": count})
                total_cost += count * cls.EXP_ITEM[exp]["cost"]

        green_count = (total_exp + min_exp_value - 1) // min_exp_value
        if green_count > 0:  # 处理最低级瓶子（向上取整，允许溢出）
            result.append({"id": cls.EXP_ITEM[min_exp_value]["id"], "num": green_count})
            total_cost += green_count * cls.EXP_ITEM[min_exp_value]["cost"]

        if total_cost > 0:
            result.append({"id": 2, "num": total_cost})
        return result
