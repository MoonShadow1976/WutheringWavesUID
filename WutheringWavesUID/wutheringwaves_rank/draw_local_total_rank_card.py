import asyncio
import time
from pathlib import Path
from typing import List, Optional, Union

from PIL import Image, ImageDraw
from pydantic import BaseModel

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img

from ..utils.util import send_master_info
from ..utils.cache import TimedCache
from ..utils.calc import WuWaCalc
from ..utils.calculate import (
    calc_phantom_score,
    get_calc_map,
)
from ..utils.database.models import WavesBind, WavesUser
from ..utils.fonts.waves_fonts import (
    waves_font_12,
    waves_font_16,
    waves_font_18,
    waves_font_20,
    waves_font_28,
    waves_font_30,
    waves_font_34,
    waves_font_58,
)
from ..utils.image import (
    GREY,
    RED,
    SPECIAL_GOLD,
    AVATAR_GETTERS,
    add_footer,
    get_ICON,
    get_square_avatar,
    get_waves_bg,
)
from ..utils.util import hide_uid
from ..wutheringwaves_config import WutheringWavesConfig
from ..utils.char_info_utils import get_all_role_detail_info_list
from ..wutheringwaves_analyzecard.user_info_utils import get_region_for_rank, get_user_detail_info

TEXT_PATH = Path(__file__).parent / "texture2d"
avatar_mask = Image.open(TEXT_PATH / "avatar_mask.png")
char_mask = Image.open(TEXT_PATH / "char_mask.png")
pic_cache = TimedCache(600, 200)

rank_length = 20  # 排行显示前20名


class BotTotalRankDetail(BaseModel):
    user_id: str
    kuro_name: str
    waves_id: str
    total_score: float
    char_score_details: List
    rank: int
    server: str = ""
    server_color: tuple = (54, 54, 54)


async def get_waves_token_condition(ev):
    wavesTokenUsersMap = {}
    flag = False

    # 群组 自定义的
    WavesRankUseTokenGroup = WutheringWavesConfig.get_config(
        "WavesRankUseTokenGroup"
    ).data
    # 全局 主人定义的
    RankUseToken = WutheringWavesConfig.get_config("RankUseToken").data
    if (
        WavesRankUseTokenGroup and ev.group_id in WavesRankUseTokenGroup
    ) or RankUseToken:
        wavesTokenUsers = await WavesUser.get_waves_all_user()
        wavesTokenUsersMap = {(w.user_id, w.uid): w.cookie for w in wavesTokenUsers}
        flag = True

    return flag, wavesTokenUsersMap


async def calculate_user_total_score(user_id, uid: str) -> Optional[BotTotalRankDetail]:
    """计算用户的练度总分"""
    role_details = await get_all_role_detail_info_list(uid)
    if not role_details:
        return None

    total_score = 0
    char_score_details = []

    # 计算每个角色的分数
    for role_detail in role_details:
        if not role_detail.phantomData or not role_detail.phantomData.equipPhantomList:
            continue

        equipPhantomList = role_detail.phantomData.equipPhantomList

        calc: WuWaCalc = WuWaCalc(role_detail)
        calc.phantom_pre = calc.prepare_phantom()
        calc.phantom_card = calc.enhance_summation_phantom_value(calc.phantom_pre)
        calc.calc_temp = get_calc_map(
            calc.phantom_card,
            role_detail.role.roleName,
            role_detail.role.roleId,
        )

        # 评分
        phantom_score = 0
        # calc_temp = get_calc_map(phantom_sum_value, role_detail.role.roleName)
        for i, _phantom in enumerate(equipPhantomList):
            if _phantom and _phantom.phantomProp:
                props = _phantom.get_props()
                _score, _bg = calc_phantom_score(
                    role_detail.role.roleId, props, _phantom.cost, calc.calc_temp
                )
                phantom_score += _score

        if phantom_score >= 175:  # 只计算分数>=175的角色
            total_score += phantom_score
            char_score_details.append({
                'char_id': role_detail.role.roleId,
                'phantom_score': phantom_score
            })

    if total_score == 0 or not char_score_details:
        return None

    # 按角色分数排序，取前10个
    char_score_details.sort(key=lambda x: x['phantom_score'], reverse=True)
    top_10_chars = char_score_details[:10]

    # 获取区服信息
    region_text, region_color = get_region_for_rank(uid)
    
    # 获取用户信息
    account_info = await get_user_detail_info(uid)

    return BotTotalRankDetail(
        user_id=user_id,  # 这里可能需要调整，根据实际需求
        kuro_name=account_info.name[:6],
        waves_id=uid,
        total_score=total_score,
        char_score_details=top_10_chars,
        rank=0,  # 排名后面统一计算
        server=region_text,
        server_color=region_color
    )


async def get_bot_total_rank_data(ev: Event, bot_bool: bool) -> List[BotTotalRankDetail]:
    """获取本地用户的练度排行数据"""
    if bot_bool:
        users = await WavesBind.get_all_data()
    else:
        users = await WavesBind.get_group_all_uid(ev.group_id)

    if not users:
        return []

    tokenLimitFlag, wavesTokenUsersMap = await get_waves_token_condition(ev)

    semaphore = asyncio.Semaphore(10)  # 限制并发数

    async def process_user(user):
        async with semaphore:
            if not user.uid:
                return []

            rank_data_list = []
            for uid in user.uid.split("_"):
                if (tokenLimitFlag and 
                    (user.user_id, uid) not in wavesTokenUsersMap):
                    continue
                try:
                    rank_data = await calculate_user_total_score(user.user_id, uid)
                    if rank_data:
                        rank_data_list.append(rank_data)
                except Exception as e:
                    logger.warning(f"用户 {user.user_id} 的UID {uid} 计算练度总分失败: {e}")
                    await send_master_info(f"用户 {user.user_id} 的UID {uid} 计算练度总分失败: {e}")

            return rank_data_list

    tasks = [process_user(user) for user in users]
    results = await asyncio.gather(*tasks)

    # 扁平化结果列表并排序
    all_rank_data = []
    for result in results:
        all_rank_data.extend(result)

    # 按总分排序
    all_rank_data.sort(key=lambda x: x.total_score, reverse=True)
    
    # 设置排名
    for rank, data in enumerate(all_rank_data, 1):
        data.rank = rank

    return all_rank_data


async def draw_local_total_rank(bot: Bot, ev: Event, bot_bool: bool = False) -> Union[str, bytes]:
    """绘制练度Bot排行"""
    self_uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)

    # 获取Bot内排行数据
    rank_all_list = await get_bot_total_rank_data(ev, bot_bool)
    if not rank_all_list:
        return f"{'Bot内' if bot_bool else '该群'}暂无角色数据或获取数据失败"

    rank_data_list = rank_all_list[:rank_length]
    if not self_uid:
        self_uid = ""
    else: # 如果用户不在前20名，添加用户数据
        for r in rank_all_list:
            if r.waves_id == self_uid and r.rank > 20:
                rank_data_list.append(r)
                break

    # 设置图像尺寸
    width = 1300
    text_bar_height = 130
    item_spacing = 120
    header_height = 510
    footer_height = 50
    char_list_len = len(rank_data_list)

    # 计算所需的总高度
    total_height = (
        header_height + text_bar_height + item_spacing * char_list_len + footer_height
    )

    # 创建带背景的画布 - 使用bg9
    card_img = get_waves_bg(width, total_height, "bg9")

    text_bar_img = Image.new("RGBA", (width, 130), color=(0, 0, 0, 0))
    text_bar_draw = ImageDraw.Draw(text_bar_img)
    # 绘制深灰色背景
    bar_bg_color = (36, 36, 41, 230)
    text_bar_draw.rounded_rectangle(
        [20, 20, width - 40, 110], radius=8, fill=bar_bg_color
    )

    # 绘制顶部的金色高亮线
    accent_color = (203, 161, 95)
    text_bar_draw.rectangle([20, 20, width - 40, 26], fill=accent_color)

    # 左侧标题
    text_bar_draw.text((40, 60), "排行说明", GREY, waves_font_28, "lm")
    text_bar_draw.text(
        (185, 50),
        "1. 综合所有角色的声骸分数。最高分为单角色最高分",
        SPECIAL_GOLD,
        waves_font_20,
        "lm",
    )
    text_bar_draw.text(
        (185, 85), "2. 显示前10个最强角色", SPECIAL_GOLD, waves_font_20, "lm"
    )

    # 备注
    temp_notes = "排行标准：以所有角色声骸分数总和（角色分数>=175）为排序的综合排名"
    text_bar_draw.text((1260, 100), temp_notes, SPECIAL_GOLD, waves_font_16, "rm")

    card_img.alpha_composite(text_bar_img, (0, header_height))

    # 导入必要的图片资源
    bar = Image.open(TEXT_PATH / "bar1.png")

    # 获取头像
    tasks = [
        get_avatar(ev, rank.user_id, rank.char_score_details[0]["char_id"]) for rank in rank_data_list
    ]
    results = await asyncio.gather(*tasks)

    # 绘制排行条目
    for rank_temp_index, temp in enumerate(zip(rank_data_list, results)):
        detail, role_avatar = temp
        y_pos = header_height + 130 + rank_temp_index * item_spacing

        # 创建条目背景
        bar_bg = bar.copy()
        bar_bg.paste(role_avatar, (100, 0), role_avatar)
        bar_draw = ImageDraw.Draw(bar_bg)

        # 绘制排名
        rank_id = detail.rank
        rank_color = (54, 54, 54)
        if rank_id == 1:
            rank_color = (255, 0, 0)
        elif rank_id == 2:
            rank_color = (255, 180, 0)
        elif rank_id == 3:
            rank_color = (185, 106, 217)

        # 排名背景
        info_rank = Image.new("RGBA", (50, 50), color=(255, 255, 255, 0))
        rank_draw = ImageDraw.Draw(info_rank)
        rank_draw.rounded_rectangle(
            [0, 0, 50, 50], radius=8, fill=rank_color + (int(0.9 * 255),)
        )
        rank_draw.text((25, 25), f"{rank_id}", "white", waves_font_34, "mm")
        bar_bg.alpha_composite(info_rank, (40, 35))

        # 绘制玩家名字
        bar_draw.text((210, 75), f"{detail.kuro_name}", "white", waves_font_20, "lm")

        # 绘制角色数量
        char_count = len(detail.char_score_details) if detail.char_score_details else 0
        bar_draw.text((210, 45), "角色数:", (255, 255, 255), waves_font_18, "lm")
        bar_draw.text((280, 45), f"{char_count}", RED, waves_font_20, "lm")

        # uid
        uid_color = "white"
        if detail.waves_id == self_uid:
            uid_color = RED
        bar_draw.text(
            (350, 40), f"特征码: {hide_uid(detail.waves_id)}", uid_color, waves_font_20, "lm"
        )

        # 区服信息
        if detail.server:
            region_block = Image.new("RGBA", (200, 30), color=(255, 255, 255, 0))
            region_draw = ImageDraw.Draw(region_block)
            region_draw.rounded_rectangle(
                [0, 0, 200, 30], radius=6, fill=detail.server_color + (int(0.9 * 255),)
            )
            region_draw.text((100, 15), f"Server: {detail.server}", "white", waves_font_18, "mm")
            bar_bg.alpha_composite(region_block, (350, 65))

        # 总分数
        bar_draw.text(
            (1180, 45),
            f"{detail.total_score:.1f}",
            (255, 255, 255),
            waves_font_34,
            "mm",
        )
        bar_draw.text((1180, 75), "总分", "white", waves_font_16, "mm")

        # 绘制角色信息
        if detail.char_score_details:
            sorted_chars = detail.char_score_details

            # 在条目底部绘制前10名角色的头像
            char_size = 40
            char_spacing = 45
            char_start_x = 570
            char_start_y = 35

            for i, char in enumerate(sorted_chars):
                char_x = char_start_x + i * char_spacing

                # 获取角色头像
                char_avatar = await get_square_avatar(char['char_id'])
                char_avatar = char_avatar.resize((char_size, char_size))

                # 应用圆形遮罩
                char_mask_img = Image.open(TEXT_PATH / "char_mask.png")
                char_mask_resized = char_mask_img.resize((char_size, char_size))
                char_avatar_masked = Image.new("RGBA", (char_size, char_size))
                char_avatar_masked.paste(char_avatar, (0, 0), char_mask_resized)

                # 粘贴头像
                bar_bg.paste(
                    char_avatar_masked, (char_x, char_start_y), char_avatar_masked
                )

                # 绘制分数
                score_text = f"{int(char['phantom_score'])}"
                bar_draw.text(
                    (char_x + char_size // 2, char_start_y + char_size + 2),
                    score_text,
                    SPECIAL_GOLD,
                    waves_font_12,
                    "mm",
                )

            # 显示最高分
            if sorted_chars:
                best_score = f"{int(sorted_chars[0]['phantom_score'])} "
                bar_draw.text((1080, 45), best_score, "lightgreen", waves_font_30, "mm")
                bar_draw.text((1080, 75), "最高分", "white", waves_font_16, "mm")

        # 贴到背景
        card_img.paste(bar_bg, (0, y_pos), bar_bg)

    # title
    title_bg = Image.open(TEXT_PATH / "totalrank.jpg")
    title_bg = title_bg.crop((0, 0, width, 500))

    # icon
    icon = get_ICON()
    icon = icon.resize((128, 128))
    title_bg.paste(icon, (60, 240), icon)

    # title
    title_text = f"#练度{'Bot' if bot_bool else '群'}排行"
    title_bg_draw = ImageDraw.Draw(title_bg)
    title_bg_draw.text((220, 290), title_text, "white", waves_font_58, "lm")

    # 时间
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    title_bg_draw.text((220, 350), f"更新于: {time_str}", GREY, waves_font_30, "lm")

    # 遮罩
    char_mask = Image.open(TEXT_PATH / "char_mask.png").convert("RGBA")
    # 根据width扩图
    char_mask = char_mask.resize((width, char_mask.height * width // char_mask.width))
    char_mask = char_mask.crop((0, char_mask.height - 500, width, char_mask.height))
    char_mask_temp = Image.new("RGBA", char_mask.size, (0, 0, 0, 0))
    char_mask_temp.paste(title_bg, (0, 0), char_mask)

    card_img.paste(char_mask_temp, (0, 0), char_mask_temp)

    card_img = add_footer(card_img)
    return await convert_img(card_img)


async def get_avatar(
    ev: Event,
    qid: Optional[Union[int, str]],
    char_id: Union[int, str],
) -> Image.Image:
    try:
        get_bot_avatar = AVATAR_GETTERS.get(ev.bot_id)

        if WutheringWavesConfig.get_config("QQPicCache").data:
            pic = pic_cache.get(qid)
            if not pic:
                pic = await get_bot_avatar(qid, size=100)
                pic_cache.set(qid, pic)
        else:
            pic = await get_bot_avatar(qid, size=100)
            pic_cache.set(qid, pic)

        # 统一处理 crop 和遮罩（onebot/discord 共用逻辑）
        pic_temp = crop_center_img(pic, 120, 120)
        img = Image.new("RGBA", (180, 180))
        avatar_mask_temp = avatar_mask.copy()
        mask_pic_temp = avatar_mask_temp.resize((120, 120))
        img.paste(pic_temp, (0, -5), mask_pic_temp)
    
    except Exception:
        # 打印异常，进行降级处理
        logger.warning("头像获取失败，使用默认头像")
        pic = await get_square_avatar(char_id)

        pic_temp = Image.new("RGBA", pic.size)
        pic_temp.paste(pic.resize((160, 160)), (10, 10))
        pic_temp = pic_temp.resize((160, 160))

        avatar_mask_temp = avatar_mask.copy()
        mask_pic_temp = Image.new("RGBA", avatar_mask_temp.size)
        mask_pic_temp.paste(avatar_mask_temp, (-20, -45), avatar_mask_temp)
        mask_pic_temp = mask_pic_temp.resize((160, 160))

        img = Image.new("RGBA", (180, 180))
        img.paste(pic_temp, (0, 0), mask_pic_temp)

    return img
