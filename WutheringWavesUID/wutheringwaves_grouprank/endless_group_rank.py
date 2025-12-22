import asyncio
from pathlib import Path

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw

from ..utils.abyss_buff import get_buff_model
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
RANK_LENGTH = 20  # 排行榜显示的最大条目数
TEXT_PATH = Path(__file__).parent / "texture2d"
BAR_IMG = Image.open(TEXT_PATH / "bar.png")
LOGO_IMG = Image.open(TEXT_PATH / "logo_small.png")
avatar_mask = Image.open(TEXT_PATH / "avatar_mask.png")
default_avatar_char_id = "1505"
pic_cache = TimedCache(86400, 200)

COLOR_QUALITY = {
    1: (188, 188, 188),
    2: (76, 175, 80),
    3: (33, 150, 243),
    4: (171, 71, 188),
    5: (255, 193, 7),
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
    """
    绘制群排行图片。

    Args:
        bot: Bot 实例。
        ev: Event 实例。
        records: 从数据库获取的排行记录列表。
        title: 图片的标题。

    Returns:
        成功时返回绘制好的图片（bytes），失败时返回错误信息（str）。
    """
    if not records:
        msg = [f"[鸣潮] 群【{ev.group_id}】暂无有效的{title}数据。"]
        msg.append(f"请使用【{PREFIX}无尽】上传更新数据后再试。")
        return "\n".join(msg)

    # 1. 数据排序和预处理
    records.sort(key=lambda i: i.score, reverse=True)

    # 2. 查找当前用户信息
    self_uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
    self_record = None
    self_rank_index = -1
    for i, record in enumerate(records):
        if record.waves_id == self_uid:
            self_record = record
            self_rank_index = i
            break

    # 3. 确定要显示的用户列表
    display_list = records[:RANK_LENGTH]
    show_self_at_end = self_record is not None

    # 4. 准备需要绘制的用户头像
    users_to_draw = display_list[:]
    if show_self_at_end and self_record not in users_to_draw:
        users_to_draw.append(self_record)

    user_qids_needed = {record.user_id for record in users_to_draw}
    user_avatar_tasks = {qid: get_avatar(ev, qid, default_avatar_char_id) for qid in user_qids_needed}
    user_avatars_results = await asyncio.gather(*user_avatar_tasks.values())
    user_avatars_map = dict(zip(user_avatar_tasks.keys(), user_avatars_results))

    # 5. 计算图片尺寸
    width = 1300
    item_spacing = 120
    header_height = 510
    footer_height = 50
    char_list_len = len(display_list) + (1 if show_self_at_end and self_record not in display_list else 0)
    total_height = header_height + item_spacing * char_list_len + footer_height

    # 6. 绘制背景和标题
    card_img = get_waves_bg(width, total_height, "bg9")
    title_bg = Image.open(TEXT_PATH / "slash.jpg").crop((0, 0, width, 500))
    icon = get_ICON().resize((128, 128))
    title_bg.paste(icon, (60, 240), icon)

    title_bg_draw = ImageDraw.Draw(title_bg)
    title_bg_draw.text((220, 290), f"#{title}", "white", waves_font_58, "lm")

    from datetime import datetime

    season_id = records[0].season_id
    end_time = datetime.fromtimestamp(season_id * 3600)
    end_time_str = f"本期截止时间: {end_time.strftime('%Y-%m-%d %H:%M')}"
    title_bg_draw.text((220, 350), end_time_str, "white", waves_font_22, "lm")

    char_mask = Image.open(TEXT_PATH / "char_mask.png").convert("RGBA")
    char_mask = char_mask.resize((width, char_mask.height * width // char_mask.width))
    char_mask = char_mask.crop((0, char_mask.height - 500, width, char_mask.height))
    char_mask_temp = Image.new("RGBA", char_mask.size, (0, 0, 0, 0))
    char_mask_temp.paste(title_bg, (0, 0), char_mask)
    card_img.paste(char_mask_temp, (0, 0), char_mask_temp)

    # 7. 绘制表头
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

    # 8. 绘制排行榜条目
    y_pos_start = 510
    for i, record in enumerate(display_list):
        user_avatar = user_avatars_map.get(record.user_id)
        if user_avatar:
            bar_image = await _create_rank_bar(record, i + 1, user_avatar, is_self_row=(record.waves_id == self_uid))
            card_img.alpha_composite(bar_image, (0, y_pos_start + i * item_spacing))

    # 9. 如果自己在榜外，单独在末尾绘制自己
    if show_self_at_end and self_record not in display_list:
        self_avatar = user_avatars_map.get(self_record.user_id)
        if self_avatar:
            bar_image = await _create_rank_bar(self_record, self_rank_index + 1, self_avatar, is_self_row=True)
            card_img.alpha_composite(bar_image, (0, y_pos_start + len(display_list) * item_spacing))

    # 10. 添加页脚并返回图片
    card_img = add_footer(card_img)
    return await convert_img(card_img)


async def get_avatar(
    ev: Event,
    qid: int | str | None,
    char_id: int | str,
) -> Image.Image:
    try:
        # 尝试从平台获取头像
        get_bot_avatar = AVATAR_GETTERS.get(ev.bot_id)
        if not get_bot_avatar:
            raise ValueError("未找到对应的头像获取器")

        # 使用带时间的缓存策略
        if WutheringWavesConfig.get_config("QQPicCache").data:
            pic = pic_cache.get(qid)
            if not pic:
                pic = await get_bot_avatar(qid, size=100)
                pic_cache.set(qid, pic)
        else:
            pic = await get_bot_avatar(qid, size=100)
            pic_cache.set(qid, pic)

        # 统一处理裁剪和遮罩
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

    # 1. 绘制排名
    rank_color = {1: (255, 0, 0), 2: (255, 180, 0), 3: (185, 106, 217)}.get(rank_num, (54, 54, 54))

    def draw_rank_id(rank_id, size, draw_pos, dest):
        info_rank = Image.new("RGBA", size, color=(255, 255, 255, 0))
        rank_draw = ImageDraw.Draw(info_rank)
        rank_draw.rounded_rectangle([0, 0, size[0], size[1]], radius=8, fill=rank_color + (int(0.9 * 255),))
        rank_draw.text(draw_pos, f"{rank_id}", "white", waves_font_34, "mm")
        role_bg.alpha_composite(info_rank, dest)

    if rank_num > 999:
        draw_rank_id("999+", (100, 50), (50, 24), (10, 30))
    elif rank_num > 99:
        draw_rank_id(rank_num, (75, 50), (37, 24), (25, 30))
    else:
        draw_rank_id(rank_num, (50, 50), (24, 24), (40, 30))

    # 2. 绘制玩家信息
    role_bg_draw.text(
        (215, 45),
        f"{record.name or hide_uid(record.waves_id)}",
        "white",
        waves_font_20,
        "lm",
    )
    uid_color = RED if is_self_row else "white"
    role_bg_draw.text((215, 75), f"{hide_uid(record.waves_id)}", uid_color, waves_font_20, "lm")

    # 3. 绘制总分
    role_bg_draw.text(
        (1060, 55),
        f"{record.score}",
        get_score_color(record.score),
        waves_font_44,
        "mm",
    )

    # 4. 绘制队伍信息
    if record.teams:
        sorted_teams = sorted(record.teams, key=lambda t: t.team_index)
        for half_index, team in enumerate(sorted_teams[:2]):
            # 绘制角色
            for role_index, role in enumerate(team.roles[:3]):
                char_model = get_char_model(role.role_id)
                if not char_model:
                    continue

                char_avatar = await get_square_avatar(role.role_id)
                char_avatar = char_avatar.resize((68, 68))

                # 绘制共鸣链
                if role.chain != -1:
                    info_block = Image.new("RGBA", (25, 25), color=(0, 0, 0, 0))
                    info_block_draw = ImageDraw.Draw(info_block)
                    info_block_draw.rectangle([0, 0, 15, 15], fill=(96, 12, 120, int(0.9 * 255)))
                    info_block_draw.text((8, 8), f"{role.chain}", "white", waves_font_12, "mm")
                    char_avatar.paste(info_block, (52, 52), info_block)

                role_bg.alpha_composite(char_avatar, (350 + half_index * 320 + role_index * 70, 20))

            # 绘制增益 (Buff)
            buff_model = get_buff_model(team.buff_id)
            if buff_model:
                buff_bg = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
                buff_bg_draw = ImageDraw.Draw(buff_bg)
                buff_bg_draw.rounded_rectangle([0, 0, 50, 50], radius=5, fill=(0, 0, 0, int(0.8 * 255)))
                buff_color = COLOR_QUALITY.get(buff_model.qualityId, (188, 188, 188))
                buff_bg_draw.rectangle([0, 45, 50, 50], fill=buff_color)
                buff_pic = (await pic_download_from_url(SLASH_PATH, buff_model.icon)).resize((50, 50))
                buff_bg.paste(buff_pic, (0, 0), buff_pic)
                role_bg.alpha_composite(buff_bg, (570 + half_index * 320, 15))

            # 绘制队伍分数
            role_bg_draw.text(
                (598 + half_index * 320, 80),
                f"{team.team_score}",
                get_score_color(team.team_score),
                waves_font_22,
                "mm",
            )

    # 5. 绘制评级
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
