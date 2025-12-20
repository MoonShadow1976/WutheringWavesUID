import asyncio
from pathlib import Path

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw

from ..utils.ascension.char import get_char_model
from ..utils.cache import TimedCache
from ..utils.database.models import WavesBind
from ..utils.fonts.waves_fonts import (
    waves_font_12,
    waves_font_20,
    waves_font_22,
    waves_font_34,
    waves_font_40,
    waves_font_44,
    waves_font_58,
)
from ..utils.image import (
    AVATAR_GETTERS,
    RED,
    SPECIAL_GOLD,
    add_footer,
    get_ICON,
    get_square_avatar,
    get_waves_bg,
    pic_download_from_url,
)
from ..utils.resource.RESOURCE_PATH import SLASH_PATH
from ..utils.util import hide_uid
from ..wutheringwaves_config import PREFIX, WutheringWavesConfig
from .models import GroupRankRecord

# --- 常量与资源加载 ---
RANK_LENGTH = 20  # 排行榜显示的长度
# 假设资源文件在同级目录的 texture2d 文件夹下
TEXT_PATH = Path(__file__).parent / "texture2d"
BAR_IMG = Image.open(TEXT_PATH / "bar.png")
LOGO_IMG = Image.open(TEXT_PATH / "logo_small.png")
avatar_mask = Image.open(TEXT_PATH / "avatar_mask.png")
default_avatar_char_id = "1505"
pic_cache = TimedCache(86400, 200)

COLOR_QUALITY = {
    1: (188, 188, 188),  # 白色
    2: (76, 175, 80),  # 绿色
    3: (33, 150, 243),  # 蓝色
    4: (171, 71, 188),  # 紫色
    5: (255, 193, 7),  # 金色
}


def get_score_color(score: int):
    if score >= 30000:
        return (255, 0, 0)
    elif score >= 25000:
        return (234, 183, 4)
    elif score >= 20000:
        return (185, 106, 217)
    elif score >= 15000:
        return (22, 145, 121)
    elif score >= 10000:
        return (53, 152, 219)
    else:
        return (255, 255, 255)


async def draw_group_rank_card(bot: Bot, ev: Event, records: list[GroupRankRecord], title: str = "海蚀无尽群排行") -> str | bytes:
    if not records:
        msg = [f"[鸣潮] 群【{ev.group_id}】暂无有效的{title}数据。"]
        msg.append(f"请使用【{PREFIX}无尽】上传更新数据后再试。")
        return "\n".join(msg)

    # 排序
    records.sort(key=lambda i: i.score, reverse=True)

    self_uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
    self_record = None
    self_rank_index = -1

    for i, record in enumerate(records):
        if record.waves_id == self_uid:
            self_record = record
            self_rank_index = i
            break

    display_list = records[:RANK_LENGTH]
    show_self_at_end = self_record is not None

    users_to_draw = display_list[:]
    if show_self_at_end:
        # 确保自己的信息在待绘制列表中，以获取头像
        if not any(u.waves_id == self_record.waves_id for u in users_to_draw):
            users_to_draw.append(self_record)

    # 准备头像
    user_qids_needed = {record.user_id for record in users_to_draw}
    user_avatar_tasks = {qid: get_avatar(ev, qid, default_avatar_char_id) for qid in user_qids_needed}
    user_avatars_results = await asyncio.gather(*user_avatar_tasks.values())
    user_avatars_map = dict(zip(user_avatar_tasks.keys(), user_avatars_results))

    # 设置图像尺寸
    width = 1300
    item_spacing = 120
    header_height = 510
    footer_height = 50
    char_list_len = len(display_list) + (1 if show_self_at_end and self_record not in display_list else 0)

    # 计算所需的总高度
    total_height = header_height + item_spacing * char_list_len + footer_height

    # 创建带背景的画布 - 使用bg9
    card_img = get_waves_bg(width, total_height, "bg9")

    # title
    title_bg = Image.open(TEXT_PATH / "slash.jpg")
    title_bg = title_bg.crop((0, 0, width, 500))

    # icon
    icon = get_ICON()
    icon = icon.resize((128, 128))
    title_bg.paste(icon, (60, 240), icon)

    # title
    title_text = f"#{title}"
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

    # 绘制表头
    header_draw = ImageDraw.Draw(card_img)
    headers = {
        64: "排名",
        224: "玩家信息",
        650: "队伍阵容",
        1056: "总评分",
        1200: "评级",
    }
    for x, text in headers.items():
        header_draw.text((x, 480), text, (255, 255, 255, 180), waves_font_34, "mm")

    # 绘制列表
    y_pos_start = 510

    for i, record in enumerate(display_list):
        user_avatar = user_avatars_map.get(record.user_id)
        if user_avatar:
            bar_image = await _create_rank_bar(record, i + 1, user_avatar, is_self_row=(record.waves_id == self_uid))
            # 使用 alpha_composite 确保透明度正确处理
            card_img.alpha_composite(bar_image, (0, y_pos_start + i * item_spacing))

    if show_self_at_end and self_record not in display_list:
        self_avatar = user_avatars_map.get(self_record.user_id)
        if self_avatar:
            bar_image = await _create_rank_bar(
                self_record,
                self_rank_index + 1,
                self_avatar,
                is_self_row=True,
            )
            card_img.alpha_composite(
                bar_image,
                (0, y_pos_start + len(display_list) * item_spacing),
            )

    card_img = add_footer(card_img)
    return await convert_img(card_img)


async def get_avatar(
    ev: Event,
    qid: int | str | None,
    char_id: int | str,
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


async def _create_rank_bar(
    record: GroupRankRecord,
    rank_num: int,
    user_avatar: Image.Image,
    is_self_row: bool = False,
) -> Image.Image:
    """创建单个排行榜条目图像"""
    role_bg = Image.open(TEXT_PATH / "bar1.png")
    role_bg.paste(user_avatar, (100, 0), user_avatar)
    role_bg_draw = ImageDraw.Draw(role_bg)

    # 添加排名显示
    rank_color = (54, 54, 54)
    if rank_num == 1:
        rank_color = (255, 0, 0)
    elif rank_num == 2:
        rank_color = (255, 180, 0)
    elif rank_num == 3:
        rank_color = (185, 106, 217)

    def draw_rank_id(rank_id, size=(50, 50), draw=(24, 24), dest=(40, 30)):
        info_rank = Image.new("RGBA", size, color=(255, 255, 255, 0))
        rank_draw = ImageDraw.Draw(info_rank)
        rank_draw.rounded_rectangle([0, 0, size[0], size[1]], radius=8, fill=rank_color + (int(0.9 * 255),))
        rank_draw.text(draw, f"{rank_id}", "white", waves_font_34, "mm")
        role_bg.alpha_composite(info_rank, dest)

    if rank_num > 999:
        draw_rank_id("999+", size=(100, 50), draw=(50, 24), dest=(10, 30))
    elif rank_num > 99:
        draw_rank_id(rank_num, size=(75, 50), draw=(37, 24), dest=(25, 30))
    else:
        draw_rank_id(rank_num, size=(50, 50), draw=(24, 24), dest=(40, 30))

    # 名字
    role_bg_draw.text((215, 45), f"{record.name or hide_uid(record.waves_id)}", "white", waves_font_20, "lm")

    # uid
    uid_color = "white"
    if is_self_row:
        uid_color = RED
    role_bg_draw.text((215, 75), f"{hide_uid(record.waves_id)}", uid_color, waves_font_20, "lm")

    # 总分数
    role_bg_draw.text(
        (1060, 55),
        f"{record.score}",
        get_score_color(record.score),
        waves_font_44,
        "mm",
    )

    if record.teams:
        # 按 team_index 排序
        sorted_teams = sorted(record.teams, key=lambda t: t.team_index)

        for half_index, team in enumerate(sorted_teams[:2]):
            # 角色
            # 限制只显示前3个角色，防止溢出
            for role_index, role in enumerate(team.roles[:3]):
                char_id = role.role_id
                char_chain = role.chain

                char_model = get_char_model(char_id)
                if char_model is None:
                    continue
                char_avatar = await get_square_avatar(char_id)
                char_avatar = char_avatar.resize((68, 68))

                if char_chain != -1:
                    info_block = Image.new("RGBA", (25, 25), color=(255, 255, 255, 0))
                    info_block_draw = ImageDraw.Draw(info_block)
                    info_block_draw.rectangle([0, 0, 15, 15], fill=(96, 12, 120, int(0.9 * 255)))
                    info_block_draw.text(
                        (8, 8),
                        f"{char_chain}",
                        "white",
                        waves_font_12,
                        "mm",
                    )
                    char_avatar.paste(info_block, (52, 52), info_block)

                role_bg.alpha_composite(char_avatar, (350 + half_index * 320 + role_index * 70, 20))

            # buff
            buff_bg = Image.new("RGBA", (60, 60), (255, 255, 255, 0))
            buff_bg_draw = ImageDraw.Draw(buff_bg)
            buff_bg_draw.rounded_rectangle(
                [0, 0, 50, 50],
                radius=5,
                fill=(0, 0, 0, int(0.8 * 255)),
            )
            buff_color = COLOR_QUALITY.get(team.buff_quality, (188, 188, 188))
            buff_bg_draw.rectangle(
                [0, 45, 50, 50],
                fill=buff_color,
            )
            buff_pic = await pic_download_from_url(SLASH_PATH, team.buff_icon)
            buff_pic = buff_pic.resize((50, 50))
            buff_bg.paste(buff_pic, (0, 0), buff_pic)

            role_bg.alpha_composite(buff_bg, (570 + half_index * 320, 15))

            # 分数
            role_bg_draw.text(
                (598 + half_index * 320, 80),
                f"{team.team_score}",
                get_score_color(team.team_score),
                waves_font_22,
                "mm",
            )

    # 评级
    if record.rank_level:
        try:
            score_img = Image.open(TEXT_PATH / f"score_{record.rank_level.lower()}.png").resize((60, 60))
            role_bg.alpha_composite(score_img, (1170, 25))
        except FileNotFoundError:
            role_bg_draw.text(
                (1200, 55),
                record.rank_level.upper(),
                SPECIAL_GOLD,
                waves_font_40,
                "mm",
            )
    else:
        role_bg_draw.text((1200, 55), "-", (128, 128, 128), waves_font_40, "mm")

    return role_bg
