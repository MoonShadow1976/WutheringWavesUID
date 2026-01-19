from pathlib import Path

from gsuid_core.logger import logger
from msgspec import json as msgjson

from .model import MonsterModel

MAP_PATH = Path(__file__).parent.parent / "map/detail_json/monster"
DICT_PATH = Path(__file__).parent.parent / "map/detail_json/monster_dict.json"
monster_id_data = {}


def read_id_dict(directory):
    # 清空原有数据
    monster_id_data.clear()

    try:
        with open(directory, encoding="utf-8") as f:
            data = msgjson.decode(f.read())
            for key, value in data.items():
                monster_id_data[key] = value
    except Exception as e:
        logger.exception(f"read_id_dict load fail decoding {directory}", e)


read_id_dict(DICT_PATH)


def get_all_monster_id_mappings() -> dict[str, list[int]]:
    """获取所有怪物ID的映射"""
    return monster_id_data.copy()


def get_all_monster_models() -> dict[str, MonsterModel]:
    """获取所有怪物模型的映射"""
    return {key: MonsterModel(**value) for key, value in monster_id_data.items()}
