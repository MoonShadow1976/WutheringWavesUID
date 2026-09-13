from pathlib import Path

from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw

from ..utils.api.model import (
    AbyssChallenge,
    AbyssFloor,
    AccountBaseInfo,
    Role,
    RoleDetailData,
    RoleList,
)
from ..utils.api.wwapi import ABYSS_TYPE_MAP, AbyssDetail, AbyssItem
from ..utils.ascension.char import get_char_model
from ..utils.char_info_utils import get_role_detail_info_with_refresh
from ..utils.error_reply import WAVES_CODE_102
from ..utils.fonts.waves_fonts import (
    waves_font_18,
    waves_font_25,
    waves_font_26,
    waves_font_30,
    waves_font_32,
    waves_font_36,
    waves_font_40,
    waves_font_42,
)
from ..utils.hint import error_reply
from ..utils.image import GOLD, GREY, add_footer, get_waves_bg
from ..utils.imagetool import draw_pic, draw_pic_with_ring
from ..utils.queues.const import QUEUE_ABYSS_RECORD
from ..utils.queues.queues import push_item
from ..utils.util import get_version
from ..utils.waves_api import waves_api
from ..wutheringwaves_analyzeabyss.abyss_data_utils import get_abyss_detail_local
from ..wutheringwaves_analyzecard.user_info_utils import get_user_detail_info
from ..wutheringwaves_config import PREFIX

TEXT_PATH = Path(__file__).parent / "texture2d"

ABYSS_ERROR_MESSAGE_NO_DATA = f"当前暂无深塔数据, 可考虑【{PREFIX}上传深塔】上传分享图\n"
ABYSS_ERROR_MESSAGE_NO_UNLOCK = "深塔暂未解锁\n"
ABYSS_ERROR_MESSAGE_NO_DEEP = "当前暂无深境区深塔数据\n"
no_login_msg = [
    "[鸣潮]",
    ">您当前为仅绑定鸣潮特征码",
    f">请使用命令【{PREFIX}登录】后查询详细深塔数据",
    "",
]
ABYSS_ERROR_MESSAGE_LOGIN = "\n".join(no_login_msg)


async def get_abyss_data(uid: str, ck: str, is_self_ck: bool):
    if is_self_ck:
        abyss_data = await waves_api.get_abyss_data(uid, ck)
    else:
        abyss_data = await waves_api.get_abyss_index(uid, ck)

    if not abyss_data.success:
        return abyss_data.throw_msg()

    abyss_data = abyss_data.data
    if not abyss_data or (isinstance(abyss_data, dict) and not abyss_data.get("isUnlock", False)):
        if not is_self_ck:
            return ABYSS_ERROR_MESSAGE_LOGIN
        return ABYSS_ERROR_MESSAGE_NO_DATA
    else:
        return AbyssChallenge.model_validate(abyss_data)


async def draw_abyss_img(ev: Event, uid: str, user_id: str, abyss_data: AbyssChallenge | None = None) -> bytes | str:
    from_local = False
    if abyss_data is not None:
        account_info = await get_user_detail_info(uid)
        role_ids = {
            r.roleId
            for d in abyss_data.difficultyList or []
            for t in d.towerAreaList
            for f in (t.floorList or [])
            for r in (f.roleList or [])
        }
        roles: list[Role] = []
        for rid in role_ids:
            cm = get_char_model(rid)
            if cm is None:
                continue
            roles.append(
                Role.model_validate(
                    {
                        "roleId": rid,
                        "level": 0,
                        "breach": 0,
                        "roleName": cm.name,
                        "roleIconUrl": "",
                        "rolePicUrl": "",
                        "starLevel": cm.starLevel,
                        "attributeId": cm.attributeId,
                        "attributeName": None,
                        "weaponTypeId": cm.weaponTypeId,
                        "weaponTypeName": None,
                        "acronym": "",
                    }
                )
            )
        role_info = RoleList.model_validate({"roleList": roles, "showToGuest": True})
        is_self_ck = False
        from_local = True
    else:
        # 尝试 CK 获取，失败则回退本地
        async def _try_ck():
            ck_res = await waves_api.get_ck_result(uid, user_id, ev.bot_id)
            is_self_ck, ck = ck_res
            if not ck:
                return None, waves_api.last_error or error_reply(WAVES_CODE_102)
            account_resp = await waves_api.get_base_info(uid, ck)
            if not account_resp.success:
                return None, account_resp.throw_msg()
            account_info = AccountBaseInfo.model_validate(account_resp.data)
            role_resp = await waves_api.get_role_info(uid, ck)
            if not role_resp.success:
                return None, role_resp.throw_msg()
            role_info = RoleList.model_validate(role_resp.data)
            abyss = await get_abyss_data(uid, ck, is_self_ck)
            if isinstance(abyss, str) or not abyss:
                return None, abyss
            if not abyss.isUnlock:
                return None, ABYSS_ERROR_MESSAGE_NO_UNLOCK
            return (account_info, role_info, abyss, is_self_ck), None

        async def _try_local():
            local_abyss = await get_abyss_detail_local(uid)
            if local_abyss is None:
                return None
            if not local_abyss.difficultyList:
                return None
            account_info = await get_user_detail_info(uid)
            # 从本地深塔数据中构建角色信息（用于显示角色头像和名称）
            role_ids = {
                r.roleId
                for d in local_abyss.difficultyList or []
                for t in d.towerAreaList
                for f in (t.floorList or [])
                for r in (f.roleList or [])
            }
            roles: list[Role] = []
            for rid in role_ids:
                cm = get_char_model(rid)
                if cm is None:
                    continue
                roles.append(
                    Role.model_validate(
                        {
                            "roleId": rid,
                            "level": 0,
                            "breach": 0,
                            "roleName": cm.name,
                            "roleIconUrl": "",
                            "rolePicUrl": "",
                            "starLevel": cm.starLevel,
                            "attributeId": cm.attributeId,
                            "attributeName": None,
                            "weaponTypeId": cm.weaponTypeId,
                            "weaponTypeName": None,
                            "acronym": "",
                        }
                    )
                )
            role_info = RoleList.model_validate({"roleList": roles, "showToGuest": True})
            return (account_info, role_info, local_abyss, False)

        if waves_api.is_net(uid):
            # 国际服，直接本地
            local_result = await _try_local()
            if local_result is None:
                return ABYSS_ERROR_MESSAGE_NO_DATA
            account_info, role_info, abyss_data, is_self_ck = local_result
            from_local = True
        else:
            # 国服，先 CK，失败则本地
            ck_result, err = await _try_ck()
            if ck_result is not None:
                account_info, role_info, abyss_data, is_self_ck = ck_result
            else:
                local_result = await _try_local()
                if local_result is not None:
                    account_info, role_info, abyss_data, is_self_ck = local_result
                    from_local = True
                else:
                    return err if isinstance(err, str) else ABYSS_ERROR_MESSAGE_NO_DATA

    command = ev.command
    text = ev.text.strip()
    difficultyName = "深境区"
    if "超载" in text or "超载" in command:
        difficultyName = "超载区"
    elif "稳定" in text or "稳定" in command:
        difficultyName = "稳定区"
    elif "实验" in text or "实验" in command:
        difficultyName = "实验区"

    if not abyss_data.difficultyList:
        return ABYSS_ERROR_MESSAGE_NO_DEEP

    abyss_check = next(
        (abyss for abyss in abyss_data.difficultyList if abyss.difficultyName == "深境区"),
        None,
    )
    if not abyss_check:
        return ABYSS_ERROR_MESSAGE_NO_DEEP

    needAbyss = None
    for _abyss in abyss_data.difficultyList:
        if _abyss.difficultyName != difficultyName:
            continue
        needAbyss = _abyss
        break
    if not needAbyss:
        return ABYSS_ERROR_MESSAGE_NO_DEEP

    frameHigh = sum([len(i.floorList) * 141 + 90 + 50 for i in needAbyss.towerAreaList if i.floorList]) + 100 + 50

    h = frameHigh + 220
    card_img = get_waves_bg(950, h, "bg4")

    # 基础信息 名字 特征码
    base_info_bg = Image.open(TEXT_PATH / "base_info_bg.png")
    base_info_draw = ImageDraw.Draw(base_info_bg)
    base_info_draw.text((275, 120), f"{account_info.name[:7]}", "white", waves_font_30, "lm")
    base_info_draw.text((226, 173), f"特征码:  {account_info.id}", GOLD, waves_font_25, "lm")
    card_img.paste(base_info_bg, (15, 20), base_info_bg)

    # 头像 头像环
    avatar, avatar_ring = await draw_pic_with_ring(ev)
    card_img.paste(avatar, (25, 70), avatar)
    card_img.paste(avatar_ring, (35, 80), avatar_ring)

    # 账号基本信息，由于可能会没有，放在一起
    if account_info.is_full:
        title_bar = Image.open(TEXT_PATH / "title_bar.png")
        title_bar_draw = ImageDraw.Draw(title_bar)
        title_bar_draw.text((660, 125), "账号等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((660, 78), f"Lv.{account_info.level}", "white", waves_font_42, "mm")

        title_bar_draw.text((810, 125), "世界等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((810, 78), f"Lv.{account_info.worldLevel}", "white", waves_font_42, "mm")
        card_img.paste(title_bar, (-20, 70), title_bar)

    # 收集当前难度深渊中需要共鸣链数据的角色ID
    needed_role_ids: list[str] = []
    for tower in needAbyss.towerAreaList:
        if not tower.floorList:
            continue
        for floor in tower.floorList:
            if floor.roleList:
                for _role in floor.roleList:
                    needed_role_ids.append(str(_role.roleId))

    # 根据面板数据获取详细信息（本地缺失的角色自动刷新）
    role_detail_info_map = await get_role_detail_info_with_refresh(ev, user_id, uid, needed_role_ids)

    # frame
    frame = Image.open(TEXT_PATH / "frame.png")
    frame = frame.resize((frame.size[0], frameHigh))

    yset = 100  # 起始
    for _abyss in abyss_data.difficultyList:
        if _abyss.difficultyName != difficultyName:
            continue
        for tower_index, tower in enumerate(_abyss.towerAreaList):
            tower_name_bg = Image.open(TEXT_PATH / f"tower_name_bg{tower.areaId}.png")
            tower_name_bg_draw = ImageDraw.Draw(tower_name_bg)
            tower_name_bg_draw.text(
                (170, 50),
                f"{difficultyName}-{tower.areaName}",
                "white",
                waves_font_36,
                "lm",
            )
            if is_self_ck or from_local:
                tower_name_bg_draw.text(
                    (500, 60),
                    f"{tower.star}/{tower.maxStar}",
                    "white",
                    waves_font_32,
                    "mm",
                )
            frame.paste(tower_name_bg, (-20, yset), tower_name_bg)

            yset += 90  # tower_name_bg high
            if not tower.floorList:
                tower.floorList = [AbyssFloor(**{"floor": 1, "picUrl": "", "star": 0, "roleList": None})]
            for floor_index, floor in enumerate(tower.floorList):
                abyss_bg = Image.open(TEXT_PATH / f"abyss_bg_{floor.floor}.jpg").convert("RGBA")
                abyss_bg = abyss_bg.resize((abyss_bg.size[0] + 100, abyss_bg.size[1]))
                abyss_bg_temp = Image.new("RGBA", abyss_bg.size)
                name_bg = Image.open(TEXT_PATH / "name_bg.png")
                name_bg_draw = ImageDraw.Draw(name_bg)
                if floor.floor == 1:
                    _floor = "一"
                elif floor.floor == 2:
                    _floor = "二"
                elif floor.floor == 3:
                    _floor = "三"
                elif floor.floor == 4:
                    _floor = "四"
                name_bg_draw.text((70, 50), f"第{_floor}层", "white", waves_font_40, "lm")
                abyss_bg_temp.paste(name_bg, (0, 0), name_bg)

                # 星数
                for i in range(3):
                    if i + 1 <= floor.star:
                        star_bg = Image.open(TEXT_PATH / "star_full.png")
                    else:
                        star_bg = Image.open(TEXT_PATH / "star_empty.png")
                    abyss_bg_temp.paste(star_bg, (10 + i * 70, 50), star_bg)

                if floor.roleList:
                    for role_index, _role in enumerate(floor.roleList):
                        role = next(
                            (role for role in role_info.roleList if role.roleId == _role.roleId),
                            None,
                        )
                        if not role:
                            continue

                        avatar = await draw_pic(role.roleId)
                        char_bg = Image.open(TEXT_PATH / f"char_bg{role.starLevel}.png")
                        char_bg_draw = ImageDraw.Draw(char_bg)
                        char_bg_draw.text((90, 150), f"{role.roleName}", "white", waves_font_18, "mm")
                        char_bg.paste(avatar, (0, 0), avatar)
                        if role_detail_info_map and str(role.roleId) in role_detail_info_map:
                            temp: RoleDetailData = role_detail_info_map[str(role.roleId)]
                            info_block = Image.new("RGBA", (40, 20), color=(255, 255, 255, 0))
                            info_block_draw = ImageDraw.Draw(info_block)
                            info_block_draw.rectangle([0, 0, 40, 20], fill=(96, 12, 120, int(0.9 * 255)))
                            info_block_draw.text(
                                (2, 10),
                                f"{temp.get_chain_name()}",
                                "white",
                                waves_font_18,
                                "lm",
                            )
                            char_bg.paste(info_block, (110, 35), info_block)

                        abyss_bg_temp.alpha_composite(char_bg, (300 + role_index * 150, -20))

                abyss_bg.paste(abyss_bg_temp, (0, 0), abyss_bg_temp)
                frame.paste(abyss_bg, (80, yset), abyss_bg)
                yset += 141
            yset += 50
        break
    else:
        if not is_self_ck and not from_local:
            return ABYSS_ERROR_MESSAGE_LOGIN
        return ABYSS_ERROR_MESSAGE_NO_DATA

    # 上传深渊记录（本地数据不上传总排行）
    if not from_local:
        await upload_abyss_record(is_self_ck, uid, difficultyName, abyss_data)

    card_img.paste(frame, (0, 210), frame)

    card_img = add_footer(card_img, 600, 20)
    card_img = await convert_img(card_img)
    return card_img


async def upload_abyss_record(
    is_self_ck: bool,
    waves_id: str,
    difficultyName: str,
    abyss_data: AbyssChallenge,
):
    from ..wutheringwaves_config import WutheringWavesConfig

    WavesToken = WutheringWavesConfig.get_config("WavesToken").data
    if not WavesToken:
        return

    if difficultyName != "深境区":
        return
    if not abyss_data:
        return
    if not abyss_data.difficultyList:
        return
    if not is_self_ck:
        return
    abyss_record = []
    for _abyss in abyss_data.difficultyList:
        if _abyss.difficultyName != difficultyName:
            continue
        for tower_index, tower in enumerate(_abyss.towerAreaList):
            if not tower.floorList:
                continue
            if len(tower.floorList) <= 1:
                continue
            floor = tower.floorList[-1]
            if floor.star == 3 and floor.roleList:
                abyss_record.append(
                    AbyssDetail.model_validate(
                        {
                            "area_type": f"{ABYSS_TYPE_MAP[tower.areaName]}{floor.floor}",
                            "area_name": tower.areaName,
                            "floor": floor.floor,
                            "char_ids": [role.roleId for role in floor.roleList],
                        }
                    )
                )

    if not abyss_record:
        return
    abyss_item = AbyssItem.model_validate(
        {
            "waves_id": waves_id,
            "abyss_record": abyss_record,
            "version": get_version(),
        }
    )
    # logger.info(f"上传深渊记录: {abyss_item.model_dump()}")
    push_item(QUEUE_ABYSS_RECORD, abyss_item.model_dump())
