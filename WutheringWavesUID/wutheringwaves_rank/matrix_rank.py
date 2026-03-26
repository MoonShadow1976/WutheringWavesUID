import asyncio
import copy
from pathlib import Path
import re

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
import httpx
from PIL import Image, ImageDraw

from ..utils.api.wwapi import (
    GET_MATRIX_RANK_URL,
    MatrixRank,
    MatrixRankItem,
    MatrixRankRes,
)
from ..utils.ascension.char import get_char_model
from ..utils.cache import TimedCache
from ..utils.database.models import WavesBind
from ..utils.fonts.waves_fonts import (
    waves_font_12,
    waves_font_18,
    waves_font_20,
    waves_font_34,
    waves_font_44,
    waves_font_58,
)
from ..utils.image import (
    AMBER,
    RED,
    WAVES_FREEZING,
    WAVES_LINGERING,
    WAVES_MOLTEN,
    WAVES_MOONLIT,
    WAVES_SIERRA,
    WAVES_VOID,
    add_footer,
    get_ICON,
    get_square_avatar,
    get_user_avatar,
    get_waves_bg,
    pic_download_from_url,
)
from ..utils.resource.RESOURCE_PATH import MATRIX_PATH
from ..utils.util import get_version
from ..wutheringwaves_abyss.draw_slash_card import COLOR_QUALITY
from ..wutheringwaves_config import WutheringWavesConfig

TEXT_PATH = Path(__file__).parent / "texture2d"
avatar_mask = Image.open(TEXT_PATH / "avatar_mask.png")
default_avatar_char_id = "1505"
pic_cache = TimedCache(600, 200)

BOT_COLOR = [
    WAVES_MOLTEN,
    AMBER,
    WAVES_VOID,
    WAVES_SIERRA,
    WAVES_FREEZING,
    WAVES_LINGERING,
    WAVES_MOONLIT,
]


def get_score_color(score: int):
    """根据分数返回颜色"""
    if score >= 58000:
        return (255, 0, 255)  # 彩色王者 - 紫红色
    elif score >= 45000:
        return (255, 215, 0)  # 金色王者 - 金色
    elif score >= 37000:
        return (255, 107, 0)  # SSS - 橙红色
    elif score >= 29000:
        return (255, 140, 0)  # SS - 橙色
    elif score >= 21000:
        return (255, 165, 0)  # S - 浅橙色
    elif score >= 16000:
        return (255, 184, 77)  # A - 浅金色
    elif score >= 12000:
        return (255, 204, 102)  # B - 淡金色
    else:
        return (255, 255, 255)  # 未达标 - 白色


async def get_rank(item: MatrixRankItem) -> MatrixRankRes | None:
    WavesToken = WutheringWavesConfig.get_config("WavesToken").data

    if not WavesToken:
        return

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                GET_MATRIX_RANK_URL,
                json=item.dict(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {WavesToken}",
                },
                timeout=httpx.Timeout(10),
            )
            if res.status_code == 200:
                return MatrixRankRes.model_validate(res.json())
            else:
                logger.warning(f"获取矩阵排行失败: {res.status_code} - {res.text}")
        except Exception as e:
            logger.exception(f"获取矩阵排行失败: {e}")


async def draw_all_matrix_rank_card(bot: Bot, ev: Event, is_global: bool = True):
    waves_id = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
    match = re.search(r"(\d+)", ev.raw_text)
    if match:
        pages = int(match.group(1))
    else:
        pages = 1
    pages = max(pages, 1)  # 最小为1
    pages = min(pages, 5)  # 最大为5
    page_num = 20

    waves_id_list = None
    if not is_global and ev.group_id:
        group_binds = await WavesBind.get_group_all_uid(group_id=ev.group_id)
        if group_binds:
            uid_set = set()
            for bind in group_binds:
                if bind.uid:
                    uids = bind.uid.split("_")
                    uid_set.update([uid for uid in uids if uid])
            waves_id_list = list(uid_set) if uid_set else None

        if not waves_id_list:
            return "本群暂无矩阵排行数据"

    item = MatrixRankItem(
        page=pages,
        page_num=page_num,
        waves_id=waves_id or "",
        version=get_version(),
        waves_id_list=waves_id_list,
    )

    rankInfoList = await get_rank(item)
    if not rankInfoList:
        return "获取矩阵排行失败"

    if rankInfoList.message and not rankInfoList.data:
        return rankInfoList.message

    if not rankInfoList.data:
        return "获取矩阵排行失败"

    # 设置图像尺寸
    width = 1300
    item_spacing = 120
    header_height = 510
    footer_height = 50
    char_list_len = len(rankInfoList.data.rank_list)

    # 计算所需的总高度
    total_height = header_height + item_spacing * char_list_len + footer_height

    # 创建带背景的画布 - 使用bg9
    card_img = get_waves_bg(width, total_height, "bg9")

    # title - 使用矩阵背景图
    try:
        title_bg = Image.open(TEXT_PATH / "matrix_bg.png").convert("RGBA")
        title_bg = crop_center_img(title_bg, width, 500)
    except:
        # 如果矩阵背景不存在，使用海墟背景
        title_bg = Image.open(TEXT_PATH / "slash.jpg")
        title_bg = title_bg.crop((0, 0, width, 500))

    # icon
    icon = get_ICON()
    icon = icon.resize((128, 128))
    title_bg.paste(icon, (60, 240), icon)

    # title
    title_text = "#矩阵总排行" if is_global else "#矩阵群排行"
    title_bg_draw = ImageDraw.Draw(title_bg)
    title_bg_draw.text((220, 290), title_text, "white", waves_font_58, "lm")

    # 遮罩
    char_mask = Image.open(TEXT_PATH / "char_mask.png").convert("RGBA")
    # 根据width扩图
    char_mask = char_mask.resize((width, char_mask.height * width // char_mask.width))
    char_mask = char_mask.crop((0, char_mask.height - 500, width, char_mask.height))
    char_mask_temp = Image.new("RGBA", char_mask.size, (0, 0, 0, 0))
    char_mask_temp.paste(title_bg, (0, 0), char_mask)

    card_img.paste(char_mask_temp, (0, 0), char_mask_temp)

    rank_list = rankInfoList.data.rank_list
    tasks = [get_avatar(rank.user_id) for rank in rank_list]
    results = await asyncio.gather(*tasks)

    # 获取角色信息
    bot_color_map = {}
    bot_color = copy.deepcopy(BOT_COLOR)

    for rank_temp_index, temp in enumerate(zip(rank_list, results)):
        rank_temp: MatrixRank = temp[0]
        role_avatar: Image.Image = temp[1]
        role_bg = Image.open(TEXT_PATH / "bar1.png")
        role_bg.paste(role_avatar, (100, 0), role_avatar)
        role_bg_draw = ImageDraw.Draw(role_bg)

        # 添加排名显示
        rank_id = rank_temp.rank
        rank_color = (54, 54, 54)
        if rank_id == 1:
            rank_color = (255, 0, 0)
        elif rank_id == 2:
            rank_color = (255, 180, 0)
        elif rank_id == 3:
            rank_color = (185, 106, 217)

        def draw_rank_id(rank_id, size=(50, 50), draw=(24, 24), dest=(40, 30)):
            info_rank = Image.new("RGBA", size, color=(255, 255, 255, 0))
            rank_draw = ImageDraw.Draw(info_rank)
            rank_draw.rounded_rectangle([0, 0, size[0], size[1]], radius=8, fill=rank_color + (int(0.9 * 255),))
            rank_draw.text(draw, f"{rank_id}", "white", waves_font_34, "mm")
            role_bg.alpha_composite(info_rank, dest)

        if rank_id > 999:
            draw_rank_id("999+", size=(100, 50), draw=(50, 24), dest=(10, 30))
        elif rank_id > 99:
            draw_rank_id(rank_id, size=(75, 50), draw=(37, 24), dest=(25, 30))
        else:
            draw_rank_id(rank_id, size=(50, 50), draw=(24, 24), dest=(40, 30))

        # 名字
        role_bg_draw.text((210, 75), f"{rank_temp.kuro_name}", "white", waves_font_20, "lm")

        # uid
        uid_color = "white"
        if rank_temp.waves_id == item.waves_id:
            uid_color = RED
        role_bg_draw.text((350, 40), f"特征码: {rank_temp.waves_id}", uid_color, waves_font_20, "lm")

        # bot主人名字
        botName = rank_temp.alias_name if rank_temp.alias_name else ""
        if botName:
            color = (54, 54, 54)
            if botName in bot_color_map:
                color = bot_color_map[botName]
            elif bot_color:
                color = bot_color.pop(0)
                bot_color_map[botName] = color

            info_block = Image.new("RGBA", (200, 30), color=(255, 255, 255, 0))
            info_block_draw = ImageDraw.Draw(info_block)
            info_block_draw.rounded_rectangle([0, 0, 200, 30], radius=6, fill=color + (int(0.6 * 255),))
            info_block_draw.text((100, 15), f"bot: {botName}", "white", waves_font_18, "mm")
            role_bg.alpha_composite(info_block, (350, 66))

        # 总分数评级图标（与矩阵卡片中的奇点扩张评分标准一致）
        score = rank_temp.total_score
        rank_icon_name = "matrix_largerempty.png"  # 默认未达标
        if score >= 58000:
            rank_icon_name = "matrix_largerkingcolor.png"  # 彩色王者
        elif score >= 45000:
            rank_icon_name = "matrix_largerkinggold.png"  # 金色王者
        elif score >= 37000:
            rank_icon_name = "matrix_sss.png"  # SSS
        elif score >= 29000:
            rank_icon_name = "matrix_ss.png"  # SS
        elif score >= 21000:
            rank_icon_name = "matrix_s.png"  # S
        elif score >= 16000:
            rank_icon_name = "matrix_a.png"  # A
        elif score >= 12000:
            rank_icon_name = "matrix_b.png"  # B

        try:
            rank_icon = Image.open(TEXT_PATH / rank_icon_name).convert("RGBA")
            # 调整图标大小
            rank_icon = rank_icon.resize((70, 70))
            role_bg.alpha_composite(rank_icon, (980, 20))
        except Exception as e:
            logger.warning(f"无法加载评级图标 {rank_icon_name}: {e}")

        # 总分数
        role_bg_draw.text(
            (1140, 55),
            f"{rank_temp.total_score}",
            get_score_color(rank_temp.total_score),
            waves_font_44,
            "mm",
        )

        # 队伍数量（显示在头像前面）
        role_bg_draw.text(
            (570, 55),
            f"队伍数量: {rank_temp.team_count}",
            (255, 255, 255),
            waves_font_20,
            "lm",
        )

        # 显示队伍角色
        team = rank_temp.team
        for role_index, char_detail in enumerate(team.char_detail):
            char_id = char_detail.char_id
            char_chain = char_detail.chain

            char_model = get_char_model(char_id)
            if char_model is None:
                continue
            char_avatar = await get_square_avatar(char_id)
            char_avatar = char_avatar.resize((45, 45))

            # 显示链度
            if char_chain != -1:
                info_block = Image.new("RGBA", (20, 20), color=(255, 255, 255, 0))
                info_block_draw = ImageDraw.Draw(info_block)
                info_block_draw.rectangle([0, 0, 20, 20], fill=(96, 12, 120, int(0.9 * 255)))
                info_block_draw.text(
                    (8, 8),
                    f"{char_chain}",
                    "white",
                    waves_font_12,
                    "mm",
                )
                char_avatar.paste(info_block, (30, 30), info_block)

            role_bg.alpha_composite(char_avatar, (720 + role_index * 50, 20))

        # buff图标
        buff_bg = Image.new("RGBA", (50, 50), (255, 255, 255, 0))
        buff_bg_draw = ImageDraw.Draw(buff_bg)
        buff_bg_draw.rounded_rectangle(
            [0, 0, 50, 50],
            radius=5,
            fill=(0, 0, 0, int(0.8 * 255)),
        )
        # 默认品质为5（金色）
        buff_color = COLOR_QUALITY.get(5, (255, 215, 0))
        buff_bg_draw.rectangle(
            [0, 45, 50, 50],
            fill=buff_color,
        )
        buff_pic = await pic_download_from_url(MATRIX_PATH, team.buff_icon)
        buff_pic = buff_pic.resize((50, 50))
        buff_bg.paste(buff_pic, (0, 0), buff_pic)

        role_bg.alpha_composite(buff_bg, (870, 15))

        # 队伍分数
        role_bg_draw.text(
            (820, 80),
            f"最高队伍得分: {team.score}",
            get_score_color(team.score),
            waves_font_20,
            "mm",
        )

        card_img.paste(role_bg, (0, 510 + rank_temp_index * item_spacing), role_bg)

    card_img = add_footer(card_img)
    card_img = await convert_img(card_img)
    return card_img


async def get_avatar(
    qid: str | None,
) -> Image.Image:
    try:
        if WutheringWavesConfig.get_config("QQPicCache").data:
            pic = pic_cache.get(qid)
            if not pic:
                pic = await get_user_avatar(qid, size=100)
                pic_cache.set(qid, pic)
        else:
            pic = await get_user_avatar(qid, size=100)
            pic_cache.set(qid, pic)

        # 统一处理 crop 和遮罩（onebot/discord 共用逻辑）
        pic_temp = crop_center_img(pic, 120, 120)
        img = Image.new("RGBA", (180, 180))
        avatar_mask_temp = avatar_mask.copy()
        mask_pic_temp = avatar_mask_temp.resize((120, 120))
        img.paste(pic_temp, (0, -5), mask_pic_temp)

    except Exception as e:
        # 打印异常，进行降级处理
        logger.warning(f"头像获取失败，使用默认头像: {e}")
        pic = await get_square_avatar(default_avatar_char_id)

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
