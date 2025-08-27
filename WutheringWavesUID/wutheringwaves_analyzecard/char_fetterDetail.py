from typing import Any
import json
import re
from pathlib import Path

from gsuid_core.logger import logger

from .detail_json import DETAIL, SONATA_COST_4_ID, SONATA_COST_3_ID, SONATA_COST_1_ID

PLUGIN_PATH =  Path(__file__).parent.parent
FETTERDETAIL_PATH = PLUGIN_PATH / "utils/map/detail_json/sonata"



async def get_fetterDetail_from_char(char_id) -> list[dict[Any, Any]]:
    
    sonata = DETAIL[char_id]['fetterDetail']

    if isinstance(sonata, dict):
        sonata_list = []
        for key, num in sonata.items():
            sonata_list.extend([await get_fetterDetail_from_sonata(key)] * num)
        return sonata_list

    return [await get_fetterDetail_from_sonata(sonata)] * 5

async def get_fetterDetail_from_sonata(sonata) -> dict:
    
    path = FETTERDETAIL_PATH / f"{sonata}.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    echo = {
        "cost": 1,
        "level": 25,
        "quality": 5,
        "fetterDetail": {
            "firstDescription": (data["set"].get("2", {}).get("desc") or ""),
            "groupId": 0,
            "iconUrl": "",
            "name": data["name"],
            "num": 5,
            "secondDescription": (data["set"].get("5", {}).get("desc") or ""),
            "tripleDescription": (data["set"].get("3", {}).get("desc") or ""),
        },
        "phantomProp": {
            "cost": 1,
            "iconUrl": "",
            "name": data["name"],
            "phantomId": 391070105,
            "phantomPropId": 0,
            "quality": 5,
            "skillDescription": "龟"
        }
    }
    return echo

async def get_first_echo_id_list(sonata_info):

    cost_4_list = []
    cost_3_list = []
    cost_1_list = []
    
    # 用于跟踪已添加的ID（避免重复）
    seen_ids = set()

    def add_unique(target, items):
        """将未出现过的ID添加到目标列表"""
        for item in items:
            if item not in seen_ids:
                seen_ids.add(item)
                target.append(item)

    if isinstance(sonata_info, dict):  # 处理多套装的情况
        for sonata_name in sonata_info.keys():
            add_unique(cost_4_list, SONATA_COST_4_ID.get(sonata_name, []))
            add_unique(cost_3_list, SONATA_COST_3_ID.get(sonata_name, []))
            add_unique(cost_1_list, SONATA_COST_1_ID.get(sonata_name, []))
    else:
        add_unique(cost_4_list, SONATA_COST_4_ID.get(sonata_info, []))
        add_unique(cost_3_list, SONATA_COST_3_ID.get(sonata_info, []))
        add_unique(cost_1_list, SONATA_COST_1_ID.get(sonata_info, []))
    
    phantom_id_list = [
        {"cost": 4, "list": cost_4_list},
        {"cost": 3, "list": cost_3_list},
        {"cost": 1, "list": cost_1_list}
    ]

    logger.debug(f"[鸣潮]获取到套装：{sonata_info}的声骸id列表：{phantom_id_list}")
    return phantom_id_list

async def echo_data_to_cost(char_id, mainProps_first, index, cost4_counter=0) -> tuple[int, int]:
    """
    根据主词条判断声骸cost并返回适配ID
    
    参数：
        char_name: str - 角色名称
        mainProps_first: dict - 主词条数据，需包含attributeName和attributeValue
        
    返回：
        tuple (echo_id, cost)
    """
    # ---------- 常量定义 ----------
    # 主词条阈值配置 . change from utils.map.calc_score_script.py
    phantom_main_value = [
        {"name": "攻击", "values": ["18%", "30%", "33%"]},
        {"name": "生命", "values": ["22.8%", "30%", "33%"]},
        {"name": "防御", "values": ["18%", "38%", "41.8%"]},
    ]
    phantom_main_value_map = {i["name"]: i["values"] for i in phantom_main_value}
    
    # 属性类型定义
    FOUR_COST_ATTRS = {"暴击", "暴击伤害", "治疗效果加成"}
    THREE_COST_PATTERNS = [r"共鸣效率", r".*伤害加成"]
    BASE_COST_ATTRS = {"攻击", "生命", "防御"}
    
    # 默认ID配置
    ECHO_ID_COST_ONE = 6000054
    ECHO_ID_COST_THREE = 6000050

    # ---------- 初始化 ----------
    key = mainProps_first[0]["attributeName"]
    value = float(mainProps_first[0]["attributeValue"].strip('%'))
    key_little = mainProps_first[1]["attributeName"] # 小词条
    
    # ---------- 获取角色配置 ----------
    try:
        # 获取完整的层级结构
        full_id_list = await get_first_echo_id_list(DETAIL[char_id]['fetterDetail'])
        # 提取 4cost 的列表
        cost_4_id_list = [echo_id for item in full_id_list if item["cost"] == 4 for echo_id in item["list"]]
        cost_3_id_list = [echo_id for item in full_id_list if item["cost"] == 3 for echo_id in item["list"]]
        # cost_1_id_list = [echo_id for item in full_id_list if item["cost"] == 1 for echo_id in item["list"]]
    except KeyError as e:
        logger.error(f"[鸣潮]角色配置数据缺失: {e}")
        return ECHO_ID_COST_ONE, 1  # 降级处理
    except FileNotFoundError:
        logger.error(f"[鸣潮]角色{DETAIL[char_id]['name']}配置文件不存在")
        return ECHO_ID_COST_ONE, 1

    # ---------- 4cost分配id逻辑 ----------
    def select_cost4_id():
        """选择cost4的ID（实现44111逻辑）"""
        needId= DETAIL[char_id].get("needId") # 指定的声骸id
        if index == 0 and needId and needId in cost_4_id_list:
            return needId
        if len(cost_4_id_list) >= 2:
            used_idx = cost4_counter % len(cost_4_id_list)  # 在列表之中循环
            if needId and needId == cost_4_id_list[used_idx]: # 如果指定了id且在列表之中
                used_idx = (used_idx + 1) % len(cost_4_id_list)
            return cost_4_id_list[used_idx]
        else:
            return cost_4_id_list[0]
    
    def select_cost3_id():
        """选择cost3的ID（实现34311逻辑）"""
        needId = DETAIL[char_id].get("needId") # 指定的声骸id
        if index == 0 and needId and needId in cost_3_id_list:
            return needId
            
        return ECHO_ID_COST_THREE

    # 处理4cost属性
    if key in FOUR_COST_ATTRS:
        return select_cost4_id(), 4
    
    # 处理3cost属性（正则匹配）
    if any(re.fullmatch(p, key) for p in THREE_COST_PATTERNS):
        return select_cost3_id(), 3
    
    # 处理基础属性
    if key in BASE_COST_ATTRS:
        try:
            thresholds = phantom_main_value_map[key]
            t1 = float(thresholds[0].strip('%'))
            t2 = float(thresholds[1].strip('%'))
            
            if value > t2:
                return select_cost4_id(), 4
            elif value > t1:
                return select_cost3_id(), 3
            elif key_little == "生命": # 声骸没拉满时
                return ECHO_ID_COST_ONE, 1
            else:
                return ECHO_ID_COST_THREE, 3
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"[鸣潮]阈值处理异常: {e}")
            return ECHO_ID_COST_ONE, 1  # 降级处理
    
    # 未知属性处理
    logger.warning(f"[鸣潮]未知主词条类型: {key}")
    return ECHO_ID_COST_ONE, 1  # 安全降级


