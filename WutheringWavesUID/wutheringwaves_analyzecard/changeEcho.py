from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.logger import logger

from ..utils.error_reply import WAVES_CODE_103
from ..utils.hint import error_reply
from ..utils.resource.RESOURCE_PATH import PLAYER_PATH
from ..wutheringwaves_config import PREFIX
from ..utils.refresh_char_detail import save_card_info
from ..utils.database.models import WavesBind
from ..utils.waves_api import waves_api
from ..utils.name_convert import (
    alias_to_char_name, 
    alias_to_sonata_name,
    phantom_id_to_phantom_name
)

from .char_fetterDetail import get_fetterDetail_from_sonata, get_first_echo_id_list

import aiofiles
import json
import copy
import re

async def change_echo(bot: Bot, ev: Event):
    at_sender = True if ev.group_id else False
    user_id = ev.at if ev.at else ev.user_id

    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
    if not uid:
        return await bot.send(error_reply(WAVES_CODE_103))

    # 更新groupid
    await WavesBind.insert_waves_uid(
        user_id, ev.bot_id, uid, ev.group_id, lenth_limit=9
    )

    if not waves_api.is_net(uid):
        return await bot.send("[鸣潮] 国服用户不支持修改角色数据\n", at_sender)

    char = ev.regex_dict.get("char")
    sonata = ev.regex_dict.get("sonata")
    phantom = bool(ev.regex_dict.get("echo"))  # 改为布尔值判断
    if not char or (not sonata and not phantom):
        return await bot.send(f"[鸣潮] 请正确使用命令,例如：\n  {PREFIX}改赞妮套装<合鸣效果> (可使用如 {PREFIX}改赞妮套装高天3不绝2 改为3+2套装,按顺序修改) \n  {PREFIX}改赞妮声骸 --修改当前套装下的首位声骸\n", at_sender)

    char_name = alias_to_char_name(char)
    if char == "漂泊者":
        char_name = char # 匹配本地用，不接受alias的结果
    char_name_print = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9\s]', '', char_name) # 删除"漂泊者·衍射"的符号

    bool_get, old_data = await get_local_all_role_detail(uid)
    if not bool_get:
        return await bot.send(f"[鸣潮] 用户{uid}数据不存在，请先使用【{PREFIX}分析】上传{char_name_print}角色数据\n", at_sender)

    char_id, roleName = await get_char_name_from_local(char_name, old_data)
    if not char_id or not roleName:
        return await bot.send(f"[鸣潮] 角色{char_name_print}不存在，请先使用【{PREFIX}分析】上传角色数据\n", at_sender)
    char_name_print = re.sub(r'[^\u4e00-\u9fa5A-Za-z0-9\s]', '', roleName) # 删除"漂泊者·衍射"的符号

    bool_change, waves_data = await change_sonata_and_first_echo(bot, char_id, sonata, phantom, old_data)
    if not bool_change or isinstance(waves_data, str):
        return await bot.send(f"[鸣潮] 修改角色{char_name_print}数据失败，{waves_data}\n", at_sender)

    # 覆盖更新
    await save_card_info(uid, waves_data)
    return await bot.send(f"[鸣潮] 修改角色{char_name_print}数据成功，使用【{PREFIX}{char_name_print}面板】查看您的角色面板\n", at_sender)

async def get_local_all_role_detail(uid: str) -> tuple[bool, dict]:
    _dir = PLAYER_PATH / uid
    _dir.mkdir(parents=True, exist_ok=True)
    path = _dir / "rawData.json"

    role_data = {}
    if path.exists():
        try:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
                data = json.loads(await f.read())
                role_data = {d["role"]["roleId"]: d for d in data}
        except Exception as e:
            logger.error(f"[鸣潮] 基础数据get failed {path}:", e)
            path.unlink(missing_ok=True)
    else:
        return False, role_data

    return True, role_data

async def get_char_name_from_local(char_name: str, role_data: dict):
    for char_id, role_info in role_data.items():
        roleName = role_info.get("role").get("roleName")
        if char_name in roleName:
            logger.info(f"[鸣潮] 角色{char_name}与{roleName}匹配")
            return int(char_id), roleName
    # 未找到匹配角色
    return None, None

async def change_sonata_and_first_echo(bot: Bot, char_id: int, sonata_a: str | None, phantom_a: bool, role_data: dict):
    # 检查角色是否存在
    if char_id not in role_data:
        return False, "角色不存在！"
    char_data = copy.deepcopy(role_data[char_id])

    # 初始化
    waves_data = []

    # 获取有效声骸列表（过滤掉空值）
    equip_phantom_list = char_data["phantomData"]["equipPhantomList"]
    valid_phantoms = [echo for echo in equip_phantom_list if echo is not None]

    if sonata_a:
        phantom_a = True  # 启用首位声骸替换
        sonata_parts = re.findall(r'([^\d]+)(\d*)', sonata_a)
        ECHO = []

        for sonata_part, num in sonata_parts:
            # 如果没有数字，默认重复1次
            num = int(num) if num else 5
            sonata = alias_to_sonata_name(sonata_part)
            if sonata:
                ECHO.extend([await get_fetterDetail_from_sonata(sonata)] * num)

        if not ECHO:
            return False, "请输入正确的套装名(合鸣效果)"
        if len(ECHO) != len(valid_phantoms):
            return False, f"套装数 {len(ECHO)}与角色有效声骸数 {len(valid_phantoms)}不一致，请考虑在套装名后紧跟声骸数量(无数字则默认为5)"
        logger.info(f"[鸣潮] 修改套装为:{sonata_parts}")

        # 只修改有效声骸
        echo_index = 0
        for i, echo in enumerate(equip_phantom_list):
            if echo is not None:
                echo["fetterDetail"] = ECHO[echo_index]["fetterDetail"]
                echo["phantomProp"]["name"] = ECHO[echo_index]["phantomProp"]["name"]
                echo_index += 1

    if phantom_a:
        sonata_exists = []
        # 构建可选项（标注cost层级 与 对应套装名称）
        sonata_group = [echo["fetterDetail"]["name"] for echo in valid_phantoms]
        phantom_id_list_groups = {}
        options = []
        flat_choices = []  # 用于存储扁平化的选项信息（cost + id）

        for sonata in sonata_group:
            if sonata not in sonata_exists:
                sonata_exists.append(sonata)
                phantom_id_list = await get_first_echo_id_list(sonata)
                
                # 存储每个套装的声骸列表，按cost分组
                phantom_id_list_groups[sonata] = phantom_id_list
                
                for group in phantom_id_list:
                    cost = group["cost"]
                    for phantom_id in group["list"]:
                        options.append(
                            f"{len(options)+1}: [套装:{sonata[:2]} {cost}c] {phantom_id_to_phantom_name(phantom_id)}"
                        )
                        flat_choices.append({"cost": cost, "id": phantom_id, "sonata": sonata})

        if not options:
            return False, "没有找到可替换的首位声骸"

        TEXT_GET_RESP = (
            "[鸣潮] 请于30秒内选择首位声骸替换为(仅提供有首位buff加成的)：\n"
            + "\n".join(options)
            + "\n请输入序号（1-{}）选择".format(len(options))
        )
        try:
            SUCCESS = False
            resp = await bot.receive_resp(reply=TEXT_GET_RESP, timeout=30)
            if resp is not None and resp.content[0].data is not None and resp.content[0].type == "text" and resp.content[0].data.isdigit():
                choice = int(resp.content[0].data) - 1
                if 0 <= choice < len(flat_choices):
                    SUCCESS = True
                    selected = flat_choices[choice]
                    target_cost = selected["cost"]
                    selected_id = selected["id"]
                    target_sonata = selected["sonata"]

                    # 获取该套装和cost层级的全部可选ID
                    same_cost_ids = []
                    if target_sonata in phantom_id_list_groups:
                        for group in phantom_id_list_groups[target_sonata]:
                            if group["cost"] == target_cost:
                                same_cost_ids = group["list"]
                                break
                    
                    if not same_cost_ids:
                        return False, f"未找到套装{target_sonata}的{target_cost}cost声骸列表"

                    # 排除已选择的声骸ID，获取其他可选声骸
                    other_phantoms = [p for p in same_cost_ids if p != selected_id]
                    
                    # 收集所有有效声骸，并按套装分类
                    sonata_to_phantoms = {}
                    for echo in valid_phantoms:
                        sonata = echo["fetterDetail"]["name"]
                        if sonata not in sonata_to_phantoms:
                            sonata_to_phantoms[sonata] = []
                        sonata_to_phantoms[sonata].append(echo)
                    
                    # 构建新的声骸顺序：将目标套装的声骸放在最前面
                    new_valid_phantoms = []
                    
                    # 首先添加目标套装的声骸（但要保持原来的内部顺序）
                    if target_sonata in sonata_to_phantoms:
                        target_phantoms = sonata_to_phantoms[target_sonata]
                        # 替换目标套装的声骸ID
                        for i, echo in enumerate(target_phantoms):
                            # 如果是该套装中第一个满足cost条件的声骸，使用selected_id
                            if i == 0 and int(echo["cost"]) == target_cost:
                                echo["phantomProp"]["phantomId"] = selected_id
                                echo["phantomProp"]["name"] = phantom_id_to_phantom_name(selected_id)
                            # 其他同套装同cost的声骸使用other_phantoms
                            elif int(echo["cost"]) == target_cost and other_phantoms:
                                echo["phantomProp"]["phantomId"] = other_phantoms[(i - 1) % len(other_phantoms)]
                                echo["phantomProp"]["name"] = phantom_id_to_phantom_name(other_phantoms[i - 1])
                        new_valid_phantoms.extend(target_phantoms)
                    
                    # 按照存在的套装添加其他套装的声骸(联动sonata_to_phantoms)
                    for sonata in sonata_exists:
                        if sonata != target_sonata and sonata in sonata_to_phantoms:
                            logger.debug(f"[鸣潮] 套装 {sonata} 添加声骸，添加数量: {len(sonata_to_phantoms[sonata])}")
                            new_valid_phantoms.extend(sonata_to_phantoms[sonata])
                    
                    # 确保长度正确
                    if len(new_valid_phantoms) != len(valid_phantoms):
                        logger.error(f"[鸣潮] 新声骸列表长度错误，预期{len(valid_phantoms)}，实际{len(new_valid_phantoms)}，构建结果：{new_valid_phantoms}")
                        return False, "声骸数量不匹配，重建列表失败"
                    
                    # 将新列表填回原位置（保持null值位置不变）
                    new_index = 0
                    for i in range(len(equip_phantom_list)):
                        if equip_phantom_list[i] is not None:
                            if new_index < len(new_valid_phantoms):
                                equip_phantom_list[i] = new_valid_phantoms[new_index]
                                new_index += 1
                    
                    logger.info(f"[鸣潮] 修改cost声骸id为:{selected_id}")

            if not SUCCESS:
                return False, "修改已关闭，请检查输入的正确性"
        except Exception:
            return False, "等待超时，修改已关闭"

    # 更新数据
    role_data[char_id] = char_data
    waves_data = list(role_data.values())

    return True, waves_data


async def get_local_all_role_info(uid: str) -> tuple[bool, dict]:
    _dir = PLAYER_PATH / uid
    _dir.mkdir(parents=True, exist_ok=True)
    path = _dir / "rawData.json"

    # 初始化标准数据结构
    role_data = {
        'roleList': [],
        'showRoleIdList': [],
        'showToGuest': False
    }
    
    if not path.exists():
        return False, role_data
        
    try:
        async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
            raw_data = json.loads(await f.read())
            
            # 正确解析角色列表
            if isinstance(raw_data, list):
                for item in raw_data:
                    if "role" in item:
                        role_data["roleList"].append(item["role"])
            
        return True, role_data
    except Exception as e:
        logger.error(f"[鸣潮] 数据解析失败 {path}:", e)
        path.unlink(missing_ok=True)
        return False, role_data



async def change_weapon_resonLevel(waves_id: str, char: str, reson_level: int):
    logger.info(f"[鸣潮] 准备修改{waves_id}{char}角色武器精炼为：{reson_level}")
    if not waves_api.is_net(waves_id):
        return "[鸣潮] 不支持修改国服用户角色武器数据!"
    
    bool_get, old_data = await get_local_all_role_detail(waves_id)
    if not bool_get:
        return f"[鸣潮] 用户{waves_id}数据不存在，请先使用【{PREFIX}分析】上传角色数据"

    # 初始化
    waves_data = []

    if "所有" in char:
        for char_id in old_data:
            # 修改
            old_data[char_id]["weaponData"]["resonLevel"] = reson_level
    else:
        char_name = alias_to_char_name(char)
        if char == "漂泊者":
            char_name = char # 匹配本地用，不接受alias的结果
        char_id, roleName = await get_char_name_from_local(char_name, old_data)
        if not char_id:
            return f"[鸣潮] 角色{char_name}不存在，请先使用【{PREFIX}分析】上传角色数据"

        # 检查角色是否存在
        if char_id not in old_data:
            return f"[鸣潮] {char_name}角色不存在！请检查命令是否正确！"

        # 修改
        old_data[char_id]["weaponData"]["resonLevel"] = reson_level

    
    waves_data = list(old_data.values())

    # 覆盖更新
    await save_card_info(waves_id, waves_data)
    return f"[鸣潮] 修改用户{waves_id}{char}角色武器精炼为{reson_level}成功！"

    