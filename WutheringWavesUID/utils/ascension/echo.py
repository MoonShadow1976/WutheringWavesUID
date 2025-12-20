from pathlib import Path

from gsuid_core.logger import logger
from msgspec import json as msgjson

from .model import EchoModel

MAP_PATH = Path(__file__).parent.parent / "map/detail_json/echo"
echo_id_data = {}
set_name_to_echo_ids: dict[str, list[int]] = {}  # 新增：套装名到声骸ID列表的映射


def read_echo_json_files(directory):
    files = directory.rglob("*.json")

    # 清空原有数据
    echo_id_data.clear()
    set_name_to_echo_ids.clear()

    for file in files:
        try:
            with open(file, encoding="utf-8") as f:
                data = msgjson.decode(f.read())
                file_name = file.name.split(".")[0]
                echo_id_data[file_name] = data

                # 新增：处理套装映射
                if "group" in data:
                    echo_id = data.get("id")
                    if echo_id:
                        for group_key, group_info in data["group"].items():
                            if "name" in group_info:
                                set_name = group_info["name"]
                                if set_name not in set_name_to_echo_ids:
                                    set_name_to_echo_ids[set_name] = []
                                if echo_id not in set_name_to_echo_ids[set_name]:
                                    set_name_to_echo_ids[set_name].append(echo_id)
        except Exception as e:
            logger.exception(f"read_echo_json_files load fail decoding {file}", e)


read_echo_json_files(MAP_PATH)


def get_echo_model(echo_id: int | str) -> EchoModel | None:
    if str(echo_id) not in echo_id_data:
        return None
    return EchoModel(**echo_id_data[str(echo_id)])


# 获取套装下的所有声骸ID
def get_echo_ids_by_set_name(set_name: str) -> list[int]:
    """根据套装名获取所有声骸ID"""
    return set_name_to_echo_ids.get(set_name, [])


# 获取所有套装映射
def get_all_set_mappings() -> dict[str, list[int]]:
    """获取所有套装名到声骸ID列表的映射"""
    return set_name_to_echo_ids.copy()
