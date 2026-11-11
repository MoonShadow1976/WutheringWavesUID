from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw

from ..utils.fonts.waves_fonts import (
    waves_font_22,
    waves_font_26,
    waves_font_36,
    waves_font_42,
)
from ..utils.image import GOLD, GREY, add_footer, get_crop_waves_bg
from ..wutheringwaves_config import PREFIX

WIDTH = 960
PADDING = 40
HEADER_H = 150
ROW_H = 100
GAP = 18
BOTTOM_H = 130


def sort_uid_list(uid_list: list[str] | None) -> list[str]:
    """按特征码数字大小升序排序(用于展示, 保证顺序固定)"""
    _uid_list = [uid for uid in (uid_list or []) if uid]
    return sorted(_uid_list, key=lambda x: int(x) if x.isdigit() else 0)


def resolve_uid_input(uid_list: list[str], text: str) -> str | None:
    """把用户输入(序号 或 特征码)解析成真实特征码, 解析失败返回None"""
    text = text.strip()
    if not text or not uid_list:
        return None

    if text in uid_list:
        return text

    if text.isdigit():
        index = int(text)
        if 1 <= index <= len(uid_list):
            return uid_list[index - 1]

    return None


async def draw_uid_list_card(
    uid_list: list[str],
    current_uid: str | None = None,
    tip: str = "",
) -> bytes:
    uid_list = sort_uid_list(uid_list)
    count = len(uid_list)
    rows_h = count * ROW_H + (count - 1) * GAP
    height = HEADER_H + rows_h + PADDING + BOTTOM_H

    card = get_crop_waves_bg(WIDTH, height, "bg").convert("RGBA")
    card = Image.alpha_composite(card, Image.new("RGBA", (WIDTH, height), (0, 0, 0, 120)))

    draw = ImageDraw.Draw(card)
    draw.text((PADDING, 56), "鸣潮特征码列表", "white", waves_font_42, anchor="lm")
    draw.text((PADDING, 108), f"共 {count} 个特征码", GREY, waves_font_22, anchor="lm")
    if tip:
        draw.text((WIDTH - PADDING, 108), tip, GOLD, waves_font_26, anchor="rm")

    row_w = WIDTH - 2 * PADDING
    y = HEADER_H
    for index, uid in enumerate(uid_list, start=1):
        is_current = uid == current_uid
        row = Image.new("RGBA", (row_w, ROW_H), (0, 0, 0, 0))
        row_draw = ImageDraw.Draw(row)
        row_draw.rounded_rectangle(
            [0, 0, row_w - 1, ROW_H - 1],
            radius=18,
            fill=(255, 200, 1, 70) if is_current else (0, 0, 0, 105),
            outline=(255, 200, 1, 255) if is_current else (255, 255, 255, 55),
            width=2,
        )

        # 序号
        row_draw.rounded_rectangle(
            [16, 16, 96, ROW_H - 16],
            radius=14,
            fill=(255, 200, 1, 100) if is_current else (255, 255, 255, 45),
        )
        row_draw.text((56, ROW_H // 2), str(index), "white", waves_font_36, anchor="mm")

        # 特征码
        row_draw.text((124, ROW_H // 2), uid, "white", waves_font_36, anchor="lm")

        # 右侧状态/操作提示
        if is_current:
            row_draw.text((row_w - 28, ROW_H // 2), "当前使用", GOLD, waves_font_26, anchor="rm")
        else:
            row_draw.text((row_w - 28, ROW_H // 2), f"{PREFIX}切换{index}", GREY, waves_font_22, anchor="rm")

        card.alpha_composite(row, (PADDING, y))
        y += ROW_H + GAP

    hint = f"{PREFIX}切换/删除+序号 操作账号"
    ImageDraw.Draw(card).text((WIDTH // 2, height - 95), hint, GREY, waves_font_22, anchor="mm")

    card = add_footer(card, 520)
    return await convert_img(card)
