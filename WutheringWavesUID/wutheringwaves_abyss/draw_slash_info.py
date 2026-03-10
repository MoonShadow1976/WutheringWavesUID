import asyncio
from datetime import datetime
import math
from pathlib import Path
import re

import aiohttp
from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw
from pydantic import BaseModel, RootModel

from ..utils.ascension.monster import get_all_monster_models
from ..utils.fonts.waves_fonts import (
    waves_font_20,
    waves_font_32,
    waves_font_42,
    waves_font_84,
)
from ..utils.image import (
    GREY,
    WAVES_CELESTIAL,
    WAVES_FREEZING,
    WAVES_MOLTEN,
    WAVES_SIERRA,
    WAVES_SINKING,
    WAVES_VOID,
    add_footer,
    get_attribute,
    pic_download_from_url,
)
from ..utils.resource.constant import ATTRIBUTE_ID_MAP
from ..utils.resource.download_file import get_monster_img
from ..utils.resource.RESOURCE_PATH import SLASH_PATH

all_monster = get_all_monster_models()

TEXT_PATH = Path(__file__).parent / "texture2d"
ATTR_PATH = Path(__file__).parent.parent / "utils" / "texture2d" / "attribute_effect"

IMG_WHIWA_BG = TEXT_PATH / "slash_bg.png"

COLOR_MAP = {
    "Fire": WAVES_MOLTEN,
    "Wind": WAVES_SIERRA,
    "Thunder": WAVES_VOID,
    "Ice": WAVES_FREEZING,
    "Light": WAVES_CELESTIAL,
    "Dark": WAVES_SINKING,
    "热熔": WAVES_MOLTEN,
    "气动": WAVES_SIERRA,
    "导电": WAVES_VOID,
    "冷凝": WAVES_FREEZING,
    "衍射": WAVES_CELESTIAL,
    "湮灭": WAVES_SINKING,
}


class SlashSchedule(BaseModel):
    Season: int
    Name: str
    start: str | None = None
    finish: str | None = None
    current: bool = False


class SlashScheduleList(RootModel):
    root: list[SlashSchedule]


class MonsterElement(BaseModel):
    Id: int
    Name: str
    Color: str
    Icon: str


class Monster(BaseModel):
    Id: int
    Name: str
    Icon: str
    Elements: list[MonsterElement]


class Buff(BaseModel):
    Id: int
    Name: str
    Desc: str
    Path: str
    Color: str


class Stage(BaseModel):
    InstId: int
    StageInfoId: int
    DungeonDesc: str
    Monsters: list[Monster]
    Buffs: list[Buff]


class Level(BaseModel):
    Id: int
    Season: int
    InstIds: list[int]
    Title: str
    Desc: str
    TargetScore: list[int]
    ScoreStage: list[str]
    OrderIndex: int
    EndLess: bool
    PreLevel: list[int]
    PassScore: int
    LevelPassReward: int
    Stages: list[Stage]


class Item(BaseModel):
    Name: str
    Icon: str
    IconMiddle: str
    IconSmall: str
    QualityId: int


class BuffItem(BaseModel):
    Id: int
    ItemId: int
    OrderIndex: int
    BuffIds: list[str]
    Item: Item


class SlashDetailResponse(BaseModel):
    Season: int
    Name: str
    StageGroups: list
    Levels: list[Level]
    BuffItems: list[BuffItem]


class ItemDetail(BaseModel):
    Id: int
    AttributesDescription: str = ""


SLASH_URL = "https://api-v2.encore.moe/api/zh-Hans/whiwa"
ITEM_URL = "https://api-v2.encore.moe/api/zh-Hans/item"


async def fetch_json(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return {}
            return await resp.json()


async def get_slash_schedule() -> dict:
    """获取排期数据，返回 { season_id: {"begin": start, "end": finish} }"""
    data = await fetch_json(SLASH_URL)
    seasons = SlashScheduleList.model_validate(data).root
    schedule = {}
    for s in seasons:
        if s.start and s.finish:
            schedule[str(s.Season)] = {"begin": s.start, "end": s.finish}
    return schedule


async def get_whiwa_detail(season_id: str) -> SlashDetailResponse | None:
    """获取单期活动详情，返回完整详情对象"""
    data = await fetch_json(f"{SLASH_URL}/{season_id}")
    if not data:
        return None
    return SlashDetailResponse.model_validate(data)


async def get_item_detail(item_id: int) -> ItemDetail:
    """获取信物详情"""
    url = f"{ITEM_URL}/{item_id}"
    data = await fetch_json(url)
    return ItemDetail.model_validate(data)


def parse_and_wrap_text(text: str, max_chars_per_line: int = 31) -> list[list[tuple[str, str]]]:
    """
    解析带颜色标签的文本（支持 <color=xxx> 和 <span style="color:#xxx;">），
    返回行列表，每行由 (文本片段, 颜色值) 元组组成。
    """
    # 预处理 span 标签
    text = re.sub(r'<span\s+style="color:\s*(#[0-9a-fA-F]{3,8})[^"]*"[^>]*>', r"<color=\1>", text)
    text = text.replace("</span>", "</color>").replace("<br>", "")

    pattern = r"(<color=(.*?)>(.*?)</color>)"
    tokens = []
    last_idx = 0

    for match in re.finditer(pattern, text):
        start, end = match.span()
        if start > last_idx:
            tokens.append({"text": text[last_idx:start], "color": "white"})
        color_key = match.group(2)
        content = match.group(3)
        tokens.append({"text": content, "color": color_key})
        last_idx = end

    if last_idx < len(text):
        tokens.append({"text": text[last_idx:], "color": "white"})

    lines = []
    current_line = []
    current_line_len = 0

    for token in tokens:
        content = token["text"]
        color = token["color"]

        for char in content:
            if current_line_len >= max_chars_per_line:
                lines.append(current_line)
                current_line = []
                current_line_len = 0
            if current_line and current_line[-1][1] == color:
                last_text, last_color = current_line[-1]
                current_line[-1] = (last_text + char, last_color)
            else:
                current_line.append((char, color))
            current_line_len += 1

    if current_line:
        lines.append(current_line)

    return lines


def draw_colored_lines(draw: ImageDraw.ImageDraw, lines: list, start_x: int, start_y: int, font):
    """绘制带颜色的行"""
    line_spacing = 40
    curr_y = start_y
    for line in lines:
        curr_x = start_x
        for text, color_key in line:
            if color_key.startswith("#"):
                fill_color = color_key
            else:
                fill_color = COLOR_MAP.get(color_key, "white")
            draw.text((curr_x, curr_y), text, fill=fill_color, font=font)
            curr_x += font.getlength(text)
        curr_y += line_spacing


def get_target_season_info(schedule_data: dict, param: str = "") -> tuple[str, str, str] | None:
    """
    根据参数确定目标赛季，返回 (season_id, begin, end)
    逻辑与深塔一致：无参数时取当前或最近一期；参数为数字时指定赛季；
    参数为下期/next 时取当前期的下一期
    """
    if not schedule_data:
        return None
    sorted_ids = sorted(schedule_data.keys(), key=lambda x: int(x))

    if param and param.isdigit():
        if param in schedule_data:
            return param, schedule_data[param]["begin"], schedule_data[param]["end"]
        return None

    now = datetime.now()
    date_format = "%Y-%m-%d"
    current_id = None

    for s_id in sorted_ids:
        info = schedule_data[s_id]
        try:
            b_date = datetime.strptime(info["begin"], date_format)
            e_date = datetime.strptime(info["end"], date_format)
            if b_date <= now <= e_date:
                current_id = s_id
                break
        except Exception:
            continue

    if current_id is None:
        for s_id in sorted_ids:
            try:
                if datetime.strptime(schedule_data[s_id]["begin"], date_format) > now:
                    current_id = s_id
                    break
            except Exception:
                continue

    if current_id is None and sorted_ids:
        current_id = sorted_ids[-1]

    if not param:
        if current_id:
            return current_id, schedule_data[current_id]["begin"], schedule_data[current_id]["end"]
        return None

    if param in ["下期", "下", "next"]:
        try:
            idx = sorted_ids.index(current_id)
            if idx + 1 < len(sorted_ids):
                nid = sorted_ids[idx + 1]
                return nid, schedule_data[nid]["begin"], schedule_data[nid]["end"]
        except Exception:
            pass

    return None


# -------------------- 绘图常量 --------------------
CARD_WIDTH = 1520  # 整个关卡卡片的宽度
STAGE_WIDTH = (CARD_WIDTH - 60) // 2  # 左右分支各占一半，间距40
CARD_PADDING = 20
CORNER_RADIUS = 15
BG_COLOR = (80, 80, 80, 100)  # 半透灰白背景

MONSTER_CARD_WIDTH = 170
MONSTER_CARD_HEIGHT = 190
MONSTER_GRID_COLS = 4
MONSTER_GRID_SPACING = 10

FONT_TITLE = waves_font_32
FONT_DESC = waves_font_32
FONT_MONSTER_NAME = waves_font_20
FONT_BUFF = waves_font_32
FONT_ITEM_NAME = waves_font_20

BUFF_LINE_SPACING = 40
BUFF_PADDING = 20
DESC_LINE_SPACING = 40


def draw_rounded_rect(img: Image.Image, xy, radius, color):
    """叠加半透明圆角矩形"""
    x1, y1, x2, y2 = xy
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=color)
    img.alpha_composite(layer, (0, 0))


def calc_monster_grid_height(monsters: list) -> int:
    """计算怪物网格高度（不含怪物时返回0）"""
    if not monsters:
        return 0
    rows = math.ceil(len(monsters) / MONSTER_GRID_COLS)
    return rows * (MONSTER_CARD_HEIGHT + MONSTER_GRID_SPACING) - MONSTER_GRID_SPACING + CARD_PADDING


def calc_stage_height(stage: Stage) -> int:
    """计算单个分支（Stage）所需高度"""
    h = 0
    if stage.DungeonDesc:
        lines = parse_and_wrap_text(stage.DungeonDesc, max_chars_per_line=31)
        h += len(lines) * BUFF_LINE_SPACING + BUFF_PADDING * 2 + CARD_PADDING
    if stage.Monsters:
        h += calc_monster_grid_height(stage.Monsters) + CARD_PADDING
    if stage.Buffs:
        total_lines = 0
        for b in stage.Buffs:
            lines = parse_and_wrap_text(b.Desc, max_chars_per_line=31)
            total_lines += len(lines)
        total_lines += len(stage.Buffs) - 1  # buff之间的空行
        h += total_lines * BUFF_LINE_SPACING + BUFF_PADDING * 2 + CARD_PADDING
    return h


def calc_level_card_height(level: Level) -> int:
    """计算单个关卡卡片的高度（不含通用描述）"""
    stage1 = level.Stages[0] if len(level.Stages) > 0 else None
    stage2 = level.Stages[1] if len(level.Stages) > 1 else None
    h1 = calc_stage_height(stage1) if stage1 else 0
    h2 = calc_stage_height(stage2) if stage2 else 0
    max_stage_height = max(h1, h2)
    title_height = 60
    # 卡片高度 = 标题区域 + 上下内边距 + 分支高度
    card_height = title_height + 2 * CARD_PADDING + max_stage_height
    return card_height


async def draw_whiwa_monsters(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    monsters: list[Monster],
    start_x: int,
    start_y: int,
):
    """绘制怪物网格（头像 + 名称 + 元素图标）"""
    if not monsters:
        return

    tasks = []
    for m in monsters:
        monster = all_monster.get(str(m.Id))
        e_id = 0
        if monster:
            e_id = monster.echo
        tasks.append(get_monster_img(int(m.Id), e_id, m.Icon))
    icons = await asyncio.gather(*tasks)

    for idx, m in enumerate(monsters):
        row = idx // MONSTER_GRID_COLS
        col = idx % MONSTER_GRID_COLS
        card_x = start_x + col * (MONSTER_CARD_WIDTH + MONSTER_GRID_SPACING)
        card_y = start_y + row * (MONSTER_CARD_HEIGHT + MONSTER_GRID_SPACING)

        if icons[idx]:
            m_icon = icons[idx].resize((128, 128))
            img.paste(m_icon, (card_x, card_y), m_icon)

        # 怪物名称
        name_x = card_x
        name_y = card_y + 155
        draw.text((name_x, name_y), m.Name, fill="white", font=FONT_MONSTER_NAME)

        # 元素图标
        if m.Elements:
            elem_start_x = name_x - 10
            elem_y = name_y - 40
            elem_size = (40, 40)
            for elem in m.Elements:
                elem_filename = ATTRIBUTE_ID_MAP[elem.Id]
                elem_img = await get_attribute(elem_filename, is_simple=True)
                elem_img = elem_img.resize(elem_size)
                img.paste(elem_img, (elem_start_x, elem_y), elem_img)
                elem_start_x += elem_size[0]


async def draw_buff_section(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    buff_descs: list[str],
    start_x: int,
    start_y: int,
    width: int,
) -> int:
    """绘制 buff 区域（半透明圆角背景 + 多行带色文本）"""
    if not buff_descs:
        return start_y

    buff_lines = []
    for desc in buff_descs:
        desc = desc.replace("\n", " ")
        lines = parse_and_wrap_text(desc, max_chars_per_line=31)
        buff_lines.extend(lines)
        if desc != buff_descs[-1]:
            buff_lines.append("")  # buff 之间空行

    # 计算高度
    line_height = BUFF_LINE_SPACING
    total_height = len(buff_lines) * line_height + BUFF_PADDING * 2

    # 绘制背景
    draw_rounded_rect(img, (start_x, start_y, start_x + width, start_y + total_height), CORNER_RADIUS, BG_COLOR)

    # 绘制文本
    text_x = start_x + BUFF_PADDING
    text_y = start_y + BUFF_PADDING
    for line in buff_lines:
        draw_colored_lines(draw, [line], text_x, text_y, FONT_BUFF)
        text_y += line_height

    return start_y + total_height + CARD_PADDING


async def draw_stage(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    stage: Stage,
    start_x: int,
    start_y: int,
    width: int,
) -> int:
    """绘制一个分支（Stage），返回分支底部 y 坐标"""
    curr_y = start_y

    if stage.DungeonDesc:
        desc_lines = parse_and_wrap_text(stage.DungeonDesc, max_chars_per_line=31)
        desc_height = len(desc_lines) * BUFF_LINE_SPACING + BUFF_PADDING * 2
        draw_rounded_rect(img, (start_x, curr_y, start_x + width, curr_y + desc_height), CORNER_RADIUS, BG_COLOR)
        text_x = start_x + BUFF_PADDING
        text_y = curr_y + BUFF_PADDING
        for line in desc_lines:
            draw_colored_lines(draw, [line], text_x, text_y, FONT_BUFF)
            text_y += BUFF_LINE_SPACING
        curr_y += desc_height + CARD_PADDING

    # 2. Buffs
    if stage.Buffs:
        buff_descs = [b.Desc for b in stage.Buffs]
        curr_y = await draw_buff_section(img, draw, buff_descs, start_x, curr_y, width)

    # 3. 怪物网格
    if stage.Monsters:
        monster_height = calc_monster_grid_height(stage.Monsters)
        await draw_whiwa_monsters(img, draw, stage.Monsters, start_x, curr_y)
        curr_y += monster_height + CARD_PADDING

    return curr_y


async def draw_level_card(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    level: Level,
    start_x: int,
    start_y: int,
) -> int:
    """绘制一个关卡卡片（不含通用描述），返回卡片底部 y 坐标"""
    card_x = start_x
    card_y = start_y
    card_w = CARD_WIDTH

    card_height = calc_level_card_height(level)

    # 绘制卡片背景
    draw_rounded_rect(img, (card_x, card_y, card_x + card_w, card_y + card_height), CORNER_RADIUS, BG_COLOR)

    # 绘制标题
    title_x = card_x + 50
    title_y = card_y + 20
    draw.text((title_x, title_y), f"{level.OrderIndex} - {level.Title}", fill="white", font=FONT_TITLE)

    # 绘制两个分支（并排）
    stage_start_y = card_y + 20 + 60 + CARD_PADDING  # 标题下方留出内边距
    stage_width = (card_w - 100 - 40) // 2

    stage1 = level.Stages[0] if len(level.Stages) > 0 else None
    stage2 = level.Stages[1] if len(level.Stages) > 1 else None

    if stage1:
        await draw_stage(img, draw, stage1, card_x + 50, stage_start_y, stage_width)
    if stage2:
        await draw_stage(img, draw, stage2, card_x + 50 + stage_width + 40, stage_start_y, stage_width)

    return card_y + card_height + CARD_PADDING


async def draw_buff_items_section(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    buff_items: list[BuffItem],
    start_x: int,
    start_y: int,
) -> int:
    """绘制信物区域（竖向排列），只展示 QualityId >=5 的信物"""
    if not buff_items:
        return start_y

    max_width = CARD_WIDTH
    # 排序（QualityId 降序，Id 升序）并过滤 QualityId >=5
    sorted_items = sorted(buff_items, key=lambda x: (-x.Item.QualityId, x.Id))
    filtered_items = [bi for bi in sorted_items if bi.Item.QualityId >= 5]
    if not filtered_items:
        return start_y

    # 并发获取详情
    tasks = [get_item_detail(bi.ItemId) for bi in filtered_items]
    details = await asyncio.gather(*tasks)

    # 布局参数
    left_margin = 20
    icon_size = 128
    right_margin = 20
    inner_padding = 20
    line_spacing = 30
    name_font = waves_font_32  # 信物名称字体
    desc_font = waves_font_20  # 描述字体

    # 右侧文字区域起始 x 坐标
    text_area_x = start_x + left_margin + icon_size + inner_padding
    text_area_width = max_width - (text_area_x - start_x) - right_margin

    # 计算每个信物高度
    item_heights = []
    for bi, detail in zip(filtered_items, details):
        # 名称高度（单行，约40px）
        name_height = 40
        # 描述文本解析
        desc_text = detail.AttributesDescription
        desc_lines = parse_and_wrap_text(desc_text, max_chars_per_line=70)
        desc_height = len(desc_lines) * line_spacing
        # 取图标高度与文字区域高度的最大值，并加上内边距
        item_height = max(icon_size, name_height + desc_height) + 2 * inner_padding
        item_heights.append(item_height)

    total_height = sum(item_heights) + BUFF_PADDING * 2

    # 绘制整个信物区域背景
    draw_rounded_rect(
        img,
        (start_x, start_y, start_x + max_width, start_y + total_height),
        CORNER_RADIUS,
        BG_COLOR,
    )

    # 并发下载所有图标
    icon_tasks = [pic_download_from_url(SLASH_PATH, bi.Item.Icon) for bi in filtered_items]
    icons = await asyncio.gather(*icon_tasks)

    # 逐个绘制信物
    current_y = start_y + BUFF_PADDING
    for idx, (bi, detail, icon_img) in enumerate(zip(filtered_items, details, icons)):
        # 图标
        icon_x = start_x + left_margin
        icon_y = current_y + inner_padding
        icon_resized = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        img.paste(icon_resized, (icon_x, icon_y), icon_resized)

        # 名称
        name = bi.Item.Name
        name_x = text_area_x - 10
        name_y = current_y + inner_padding
        draw.text((name_x, name_y), name, fill="white", font=name_font)

        # 描述
        desc_text = detail.AttributesDescription
        desc_lines = parse_and_wrap_text(desc_text, max_chars_per_line=70)
        desc_y = name_y + 50  # 名称下方留一点间距（名称高度约40）
        for line in desc_lines:
            draw_colored_lines(draw, [line], name_x, desc_y, desc_font)
            desc_y += line_spacing

        current_y += item_heights[idx]

    return start_y + total_height + CARD_PADDING


async def draw_slash_info_img(param: str = "", mode: str = "whiwa") -> str | bytes:
    if mode != "whiwa":
        return "请使用活动相关指令查看。"

    schedule = await get_slash_schedule()
    if not schedule:
        return "获取活动排期失败，API可能无法访问。"

    clean_param = param.replace("信息", "").strip()
    season_info = get_target_season_info(schedule, clean_param)
    if not season_info:
        return "未查询到有效的活动排期数据。"

    s_id, s_begin, s_end = season_info
    detail = await get_whiwa_detail(s_id)
    if not detail:
        return f"获取活动第 {s_id} 期详情失败。"

    # 关卡按 OrderIndex 倒序排列
    levels = sorted(detail.Levels, key=lambda x: x.OrderIndex, reverse=True)
    buff_items = detail.BuffItems

    # 获取通用描述（所有关卡相同，取第一个即可）
    common_desc = levels[0].Desc if levels else ""

    # 计算总高度
    title_height = 240

    # 通用描述高度
    desc_height = 0
    if common_desc:
        desc_lines = parse_and_wrap_text(common_desc, max_chars_per_line=47)
        desc_height = len(desc_lines) * DESC_LINE_SPACING + BUFF_PADDING * 2

    # 信物区域高度
    buff_section_height = 0
    if buff_items:
        # 只考虑 QualityId >=5 的
        filtered = [bi for bi in buff_items if bi.Item.QualityId >= 5]
        if filtered:
            # 保守估算每个信物高度 150px（图标128 + 名称与描述40 + 边距）
            buff_section_height = len(filtered) * 150 + BUFF_PADDING * 2 + CARD_PADDING

    # 关卡卡片总高度
    levels_height = 0
    for level in levels:
        levels_height += calc_level_card_height(level) + CARD_PADDING

    total_height = title_height + desc_height + buff_section_height + levels_height + 200  # 底部留白

    width = CARD_WIDTH + 180
    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 255))

    if IMG_WHIWA_BG.exists():
        bg = Image.open(IMG_WHIWA_BG).resize((width, total_height))
        img.paste(bg, (0, 0))

    draw = ImageDraw.Draw(img)

    # 绘制标题
    title_text = f"冥歌海墟 · 第 {s_id} 期"
    date_text = f"{s_begin} ~ {s_end}"
    draw.text((100, 80), title_text, fill="white", font=waves_font_84)
    draw.text((100, 180), date_text, fill=GREY, font=waves_font_42)

    current_y = 240

    # 绘制通用描述
    if common_desc:
        desc_lines = parse_and_wrap_text(common_desc, max_chars_per_line=47)
        desc_height = len(desc_lines) * DESC_LINE_SPACING + BUFF_PADDING * 2
        draw_rounded_rect(img, (100, current_y, 100 + CARD_WIDTH, current_y + desc_height), CORNER_RADIUS, BG_COLOR)
        desc_text_x = 100 + BUFF_PADDING
        desc_text_y = current_y + BUFF_PADDING
        for line in desc_lines:
            draw_colored_lines(draw, [line], desc_text_x, desc_text_y, FONT_DESC)
            desc_text_y += DESC_LINE_SPACING
        current_y += desc_height + CARD_PADDING

    # 绘制信物区域
    if buff_items:
        current_y = await draw_buff_items_section(img, draw, buff_items, 100, current_y)

    # 绘制关卡卡片
    for level in levels:
        current_y = await draw_level_card(img, draw, level, start_x=100, start_y=current_y)

    img = add_footer(img, 1000, 10, color="encore")
    img = img.resize((int(width * 0.75), int(total_height * 0.75)))
    return await convert_img(img)
