
import json
import aiofiles
from typing import  List, Union

from gsuid_core.logger import logger

from ..utils.resource.RESOURCE_PATH import PLAYER_PATH
from ..utils.util import async_func_lock


@async_func_lock(keys=["uid"])
async def delete_char_detail(
    uid: str,
    delete_type: Union[str, List[str]] = "all",
) -> str:
    _dir = PLAYER_PATH / uid
    _dir.mkdir(parents=True, exist_ok=True)
    path = _dir / "rawData.json"

    # 读取现有数据
    old_data = {}
    if path.exists():
        try:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
                content = await f.read()
                if content.strip():  # 确保文件不为空
                    old = json.loads(content)
                    old_data = {d["role"]["roleId"]: d for d in old}
        except Exception as e:
            logger.exception(f"读取角色数据失败 {path}: {e}")
            # 只有在文件损坏时才删除
            try:
                path.unlink(missing_ok=True)
                return "角色数据文件损坏，已删除，请重新添加角色\n"
            except Exception as unlink_error:
                logger.error(f"删除损坏文件失败 {path}: {unlink_error}")
            return "读取角色数据失败，请稍后再试\n"

    # 记录原始数据长度和内容（用于比较）
    original_count = len(old_data)
    original_role_ids = set(old_data.keys())

    # 确定需要处理的角色
    if delete_type == "all":
        # 清空所有角色数据
        save_data = []
    elif isinstance(delete_type, list):
        # 只删除指定的角色
        delete_type_str = [str(x) for x in delete_type]  # 统一转换为字符串
        save_data = [
            role_data for role_id, role_data in old_data.items() 
            if str(role_id) not in delete_type_str
        ]
    else:
        logger.warning(f"无效的 refresh_type: {delete_type}")
        return f"无效的删除角色: {delete_type}\n"

    # 计算删除后的角色ID集合
    remaining_role_ids = {str(role_data["role"]["roleId"]) for role_data in save_data}
    
    # 检查是否有变化
    if delete_type == "all":
        # 如果是删除所有，只要原始有数据就表示有变化
        has_changed = original_count > 0
    else:
        # 对于部分删除，检查剩余角色ID是否与原始不同
        has_changed = remaining_role_ids != original_role_ids
    
    # 如果没有变化，直接返回
    if not has_changed:
        if delete_type == "all":
            return "没有角色数据可删除\n"
        else:
            return "没有找到要删除的角色\n"

    # 保存更新后的数据
    try:
        async with aiofiles.open(path, "w", encoding="utf-8") as file:
            await file.write(json.dumps(save_data, ensure_ascii=False, indent=2))
        logger.info(f"成功删除角色数据，UID: {uid}, 操作: {delete_type}")
        
        # 计算删除的数量
        deleted_count = original_count - len(save_data)
        if delete_type == "all":
            return f"已删除所有角色数据（共{original_count}个角色）\n"
        else:
            return f"删除成功，共删除了{deleted_count}个角色\n"
            
    except Exception as e:
        logger.exception(f"保存角色数据失败 {path}: {e}")
        return "删除角色失败，请稍后再试\n"
