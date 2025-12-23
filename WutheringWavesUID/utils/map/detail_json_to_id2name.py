import json
from pathlib import Path

DETAIL_PATH = Path(__file__).parent / "detail_json"
CHAR_DETAIL_PATH = DETAIL_PATH / "char"
WEAPON_DETAIL_PATH = DETAIL_PATH / "weapon"
ECHO_DETAIL_PATH = DETAIL_PATH / "echo"
MATERIAL_DETAIL_PATH = DETAIL_PATH / "material"

ID_NAME_PATH = Path(__file__).parent / "id2name.json"


def process_json_files(directory):
    """处理指定目录下的所有json文件，提取id和name映射"""
    id_name_map = {}

    # 遍历目录下所有json文件
    for json_file in directory.glob("*.json"):
        try:
            # 读取json文件
            data = json.loads(json_file.read_text(encoding="utf-8"))

            # 提取id和name
            # 文件名去除扩展名作为id
            file_id = json_file.stem

            # 从json数据中获取name字段
            if "name" in data:
                name = data["name"]
                id_name_map[file_id] = name

        except Exception as e:
            print(f"处理文件 {json_file} 时出错: {e}")
            continue

    return id_name_map


def generate_id2name_mapping():
    """生成完整的id到name的映射"""
    # 确保父目录存在
    ID_NAME_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 分别处理四个类别的文件
    char_mapping = process_json_files(CHAR_DETAIL_PATH)
    weapon_mapping = process_json_files(WEAPON_DETAIL_PATH)
    echo_mapping = process_json_files(ECHO_DETAIL_PATH)
    material_mapping = process_json_files(MATERIAL_DETAIL_PATH)

    # 按照要求顺序合并映射
    # 角色 -> 武器 -> 声骸 -> 材料
    full_mapping = {}

    # 合并角色映射（按id排序）
    for char_id in sorted(char_mapping.keys()):
        full_mapping[char_id] = char_mapping[char_id]

    # 合并武器映射（按id排序）
    for weapon_id in sorted(weapon_mapping.keys()):
        full_mapping[weapon_id] = weapon_mapping[weapon_id]

    # 合并声骸映射（按id排序）
    for echo_id in sorted(echo_mapping.keys()):
        full_mapping[echo_id] = echo_mapping[echo_id]

    # 合并材料映射（按id排序）
    for material_id in sorted(material_mapping.keys()):
        full_mapping[material_id] = material_mapping[material_id]

    # 写入文件
    with open(ID_NAME_PATH, "w", encoding="utf-8") as f:
        json.dump(full_mapping, f, ensure_ascii=False, indent=2)

    print(f"成功生成映射文件，共 {len(full_mapping)} 条记录")
    print(f"角色: {len(char_mapping)} 条")
    print(f"武器: {len(weapon_mapping)} 条")
    print(f"声骸: {len(echo_mapping)} 条")
    print(f"材料: {len(material_mapping)} 条")

    return full_mapping


if __name__ == "__main__":
    # 生成id到name的映射
    mapping = generate_id2name_mapping()
