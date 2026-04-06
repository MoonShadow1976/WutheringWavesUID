from pathlib import Path

from gsuid_core.logger import logger
from msgspec import json as msgjson

from .model import Material

MATERIAL_PATH = Path(__file__).parent.parent / "map/detail_json/material"
material_data = {}


def read_material_json_files(directory: Path):
    """遍历目录下所有 .json 文件，读取材料数据并存入全局字典"""
    files = directory.rglob("*.json")

    for file in files:
        try:
            with open(file, encoding="utf-8") as f:
                data = msgjson.decode(f.read())
                file_name = file.name.split(".")[0]  # 以文件名（不含扩展名）作为 key
                material_data[file_name] = data
        except Exception as e:
            logger.exception(f"read_material_json_files failed to decode {file}", e)


read_material_json_files(MATERIAL_PATH)


def get_material_model(material_id: int | str) -> Material | None:
    if str(material_id) not in material_data:
        return None
    return Material(**material_data[str(material_id)])
