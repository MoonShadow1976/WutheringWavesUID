import copy
from pathlib import Path

from gsuid_core.logger import logger
from msgspec import json as msgjson

from ..ascension.constant import fixed_name, sum_percentages
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
        return int(desc[brace_start+1:brace_end])
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

    # 技能树 check from wutheringwaves_wiki\draw_char.py keys
    # 技能树映射：breach阈值 -> 技能键列表
    skill_tree_map = {
        0: ["1", "2", "3", "6", "7", "8", "17"],
        2: ["4", "10", "11"],
        3: ["9", "12"],
        4: ["5", "14", "15"],
        5: ["13", "16"]
    }

    # 构建skill_tree列表
    skill_tree = []
    for threshold, keys in skill_tree_map.items():
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
