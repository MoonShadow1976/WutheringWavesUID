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
    waves_font_18,
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
)
from ..utils.resource.constant import ATTRIBUTE_ID_MAP
from ..utils.resource.download_file import get_monster_img

all_monster = get_all_monster_models()

TEXT_PATH = Path(__file__).parent / "texture2d"
ATTR_PATH = Path(__file__).parent.parent / "utils" / "texture2d" / "attribute_effect"

IMG_TOWER_BG = TEXT_PATH / "tower_bg.png"
IMG_EDGE_BG = TEXT_PATH / "edge_bg.png"
IMG_CENTER_BG = TEXT_PATH / "center_bg.png"

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


class TowerSchedule(BaseModel):
    """赛季信息"""

    id: int
    name: str
    areas: int
    start: str | None = ""
    finish: str | None = ""
    current: bool = False


class TowerScheduleList(BaseModel):
    """排期接口返回数据"""

    seasons: list[TowerSchedule]


class MonsterProp(BaseModel):
    """怪物属性条目"""

    attributeType: int
    key: str
    name: str
    value: int
    isPercent: bool
    icon: str = ""


class MonsterElement(BaseModel):
    """怪物元素"""

    id: int
    name: str
    icon: str


class Monster(BaseModel):
    """怪物数据"""

    id: int
    name: str
    icon: str
    elements: list[MonsterElement] = []
    whiteGreenProps: list[MonsterProp] = []
    Level: int = 0  # 后续处理添加
    Life: int = 0  # 后续处理添加
    element_list: list[int] = []  # 后续处理添加


class Buff(BaseModel):
    """Buff 数据"""

    id: int
    name: str = ""
    desc: str = ""
    icon: str = ""


class Target(BaseModel):
    """挑战目标"""

    id: int
    score: int
    desc: str
    rawDesc: str
    params: list[int]


class Challenge(BaseModel):
    """单层挑战实例"""

    id: int
    instanceId: int
    season: int
    areaNum: int
    floor: int
    cost: int
    difficulty: int
    areaName: str
    monsters: list[Monster] = []
    buffs: list[Buff] = []
    targets: list[Target] = []
    bgPath: str = ""
    itemBgPath: str = ""


class TowerDetailResponse(RootModel):
    """赛季详情数据：区域号 -> 楼层号 -> 子层标识 -> 挑战列表"""

    root: dict[str, dict[str, dict[str, list[Challenge]]]]


class AreaDetail(BaseModel):
    """区域数据"""

    monsters: list[Monster] = []
    buffs: dict[str, Buff] = {}


TOWER_URL = "https://api-v2.encore.moe/api/zh-Hans/toa"


async def fetch_json(url: str) -> dict:
    """通用异步 GET 请求，返回 JSON 数据"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return {}
            return await resp.json()


async def get_tower_schedule() -> dict:
    """
    从新 API 获取排期数据，转换为格式：
    { season_id: {"begin": start, "end": finish} }
    """
    data = await fetch_json(TOWER_URL)

    resp = TowerScheduleList.model_validate(data)

    return {str(s.id): {"begin": s.start, "end": s.finish} for s in resp.seasons}


async def get_tower_detail(season_id: str) -> dict[str, dict[str, AreaDetail]] | None:
    """从新 API 获取单期深塔详情"""
    data = await fetch_json(f"{TOWER_URL}/{season_id}")

    # 直接验证赛季数据部分（data.get(season_id, {})）
    season_data = TowerDetailResponse.model_validate(data.get(season_id, {}))

    areas: dict[str, dict[str, AreaDetail]] = {}
    for area_num, area_data in season_data.root.items():
        floors: dict[str, AreaDetail] = {}
        for floor_num, floor_data in area_data.items():
            # 每个 floor_data 可能包含多个子层（如不同难度），通常只有一个
            for _, value in floor_data.items():
                for instance in value:
                    buffs = {str(i + 1): b for i, b in enumerate(instance.buffs)}
                    monsters = []
                    for monster in instance.monsters:
                        for prop in monster.whiteGreenProps:
                            if prop.key == "LifeMax":
                                monster.Life = prop.value
                            elif prop.key == "Lv":
                                monster.Level = prop.value
                            monster.element_list = [e.id for e in monster.elements]
                        monsters.append(monster)
            floors[floor_num] = AreaDetail(monsters=monsters, buffs=buffs)
        areas[area_num] = floors

    return areas


def parse_and_wrap_text(text: str, max_chars_per_line: int = 24) -> list[list[tuple[str, str]]]:
    """
    解析带颜色标签的文本，支持 <color=xxx> 和 <span style="color:#xxx;"> 两种格式。
    返回行列表，每行由 (文本片段, 颜色值) 元组组成。
    """
    # 预处理：将 span 标签转换为 color 标签，兼容分号在引号外及 3-8 位颜色值
    text = re.sub(r'<span\s+style="color:\s*(#[0-9a-fA-F]{3,8})[^"]*"[^>]*>', r"<color=\1>", text)
    text = text.replace("</span>", "</color>")

    # 原有颜色标签解析（保持不变）
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

    # 按字符拆分成行，合并同色连续字符（保持不变）
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
    """
    绘制带颜色的行，颜色可以是颜色名或十六进制字符串。
    """
    line_spacing = 40
    curr_y = start_y

    for line in lines:
        curr_x = start_x
        for text, color_key in line:
            # 如果颜色是十六进制代码，直接使用；否则从映射中获取
            if color_key.startswith("#"):
                fill_color = color_key
            else:
                fill_color = COLOR_MAP.get(color_key, "white")
            draw.text((curr_x, curr_y), text, fill=fill_color, font=font)
            curr_x += font.getlength(text)
        curr_y += line_spacing


def get_target_season_info(schedule_data: dict, param: str = "") -> tuple[str, str, str] | None:
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


# --- 绘图常量 ---
COL_WIDTH = 1000
CARD_PADDING = 20
CORNER_RADIUS = 15
BG_COLOR = (80, 80, 80, 100)  # 半透灰白色背景
MONSTER_CARD_WIDTH = 170
MONSTER_CARD_HEIGHT = 190
MONSTER_GRID_COLS = 5
MONSTER_GRID_SPACING = 10
BUFF_PADDING = 20
FLOOR_TITLE_FONT = waves_font_32
MONSTER_NAME_FONT = waves_font_20
MONSTER_STATS_FONT = waves_font_18
BUFF_TEXT_FONT = waves_font_32
BUFF_LINE_SPACING = 40


def draw_rounded_rect(img: Image.Image, xy, radius, color):
    """在 img 上叠加半透明圆角矩形（确保 alpha 生效）"""
    x1, y1, x2, y2 = xy
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    # 绘制圆角矩形
    layer_draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=color)
    img.alpha_composite(layer, (0, 0))


def calc_monster_grid_height(monsters: list[Monster]) -> int:
    """仅计算怪物网格占据的高度（不绘制）"""
    if not monsters:
        return 0
    cols = MONSTER_GRID_COLS
    card_h = MONSTER_CARD_HEIGHT
    spacing = MONSTER_GRID_SPACING
    rows = math.ceil(len(monsters) / cols)
    return rows * (card_h + spacing) - spacing + CARD_PADDING


async def draw_floor_monsters(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    monsters: list[Monster],
    start_x: int,
    start_y: int,
):
    """绘制怪物网格（每个怪物独立卡片背景）"""
    if not monsters:
        return

    cols = MONSTER_GRID_COLS
    card_w = MONSTER_CARD_WIDTH
    card_h = MONSTER_CARD_HEIGHT
    spacing = MONSTER_GRID_SPACING

    # 异步获取所有怪物头像
    tasks = []
    for m in monsters:
        monster = all_monster.get(str(m.id))
        e_id = 0
        if monster:
            e_id = monster.echo
        tasks.append(get_monster_img(int(m.id), e_id, m.icon))
    icons = await asyncio.gather(*tasks)

    for idx, m_data in enumerate(monsters):
        row = idx // cols
        col = idx % cols
        card_x = start_x + col * (card_w + spacing)
        card_y = start_y + row * (card_h + spacing)

        # 绘制怪物卡片背景（圆角矩形）
        # draw_rounded_rect(img, (card_x, card_y, card_x + card_w, card_y + card_h), CORNER_RADIUS, BG_COLOR)

        # 怪物头像
        if icons[idx]:
            m_icon = icons[idx].resize((128, 128))
            img.paste(m_icon, (card_x, card_y), m_icon)

        # 怪物名称
        name_x = card_x
        name_y = card_y + 155
        draw.text((name_x, name_y), m_data.name, fill="white", font=MONSTER_NAME_FONT)

        # 元素图标
        element_ids = m_data.element_list
        if element_ids:
            name_w = MONSTER_NAME_FONT.getlength(m_data.name)
            elem_start_x = name_x - 10
            elem_y = name_y - 40
            elem_size = (40, 40)
            for eid in element_ids:
                elem_filename = ATTRIBUTE_ID_MAP[eid]
                elem_img = await get_attribute(elem_filename, is_simple=True)
                elem_img = elem_img.resize(elem_size)
                img.paste(elem_img, (elem_start_x, elem_y), elem_img)
                elem_start_x += elem_size[0]

        # 等级和生命
        stats_x = name_x
        stats_y = name_y + 22
        draw.text((stats_x, stats_y), f"等级 {m_data.Level}", fill="white", font=MONSTER_STATS_FONT)
        draw.text((stats_x, stats_y + 20), f"生命 {int(m_data.Life)}", fill="white", font=MONSTER_STATS_FONT)


async def draw_buff_section(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    buff_list: list[str],
    start_x: int,
    start_y: int,
) -> int:
    """
    绘制buff区域（半透明圆角背景 + 多行带色文本）
    返回下一内容的起始y坐标（即本区域底部 + 间距）
    """
    if not buff_list:
        return start_y

    # 解析每个buff的文本行
    buff_lines = []
    for buff_desc in buff_list:
        desc = buff_desc.replace("\n", " ")
        lines = parse_and_wrap_text(desc, max_chars_per_line=31)
        buff_lines.extend(lines)  # 每个buff可能占多行
        if buff_desc != buff_list[-1]:
            buff_lines.append("")  # 每个buff之间加空行

    # 计算所需高度
    line_height = BUFF_LINE_SPACING
    total_height = len(buff_lines) * line_height + BUFF_PADDING * 2

    # 绘制背景矩形
    bg_x = start_x
    bg_y = start_y
    bg_w = COL_WIDTH

    draw_rounded_rect(img, (bg_x, bg_y, bg_x + bg_w, bg_y + total_height), CORNER_RADIUS, BG_COLOR)
    # 绘制文本
    text_x = bg_x + BUFF_PADDING
    text_y = bg_y + BUFF_PADDING
    for line in buff_lines:
        draw_colored_lines(draw, [line], text_x, text_y, BUFF_TEXT_FONT)
        text_y += line_height

    return bg_y + total_height + CARD_PADDING


async def draw_floor_item(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    floors: dict[str, AreaDetail],
    data_key: str,
    display_num: int,
    col_start_x: int,
    floor_y: int,
) -> int:
    """绘制单个楼层卡片（含标题 + 怪物网格）"""
    floor_data = floors.get(data_key)
    if not floor_data or not floor_data.monsters:
        return floor_y

    # 1. 计算怪物网格高度（不绘制）
    monster_height = calc_monster_grid_height(floor_data.monsters)
    if monster_height == 0:
        return floor_y

    # 2. 计算楼层卡片总高度
    title_height = 60
    card_height = title_height + monster_height + CARD_PADDING * 2

    # 3. 绘制楼层卡片背景（半透明圆角矩形）
    card_x = col_start_x
    card_y = floor_y
    card_w = COL_WIDTH
    draw_rounded_rect(img, (card_x, card_y, card_x + card_w, card_y + card_height), CORNER_RADIUS, BG_COLOR)

    # 4. 绘制楼层标题
    title_x = card_x + 50
    title_y = card_y + 20
    draw.text((title_x, title_y), f"{display_num}F", fill="white", font=FLOOR_TITLE_FONT)

    # 5. 绘制怪物网格（实际绘制）
    await draw_floor_monsters(
        img,
        draw,
        floor_data.monsters,
        col_start_x + 50,
        floor_y + 55,  # 注意：相对于背景内部偏移
    )

    return card_y + card_height + CARD_PADDING


async def draw_tower_column(
    img: Image.Image, draw: ImageDraw.ImageDraw, area_data: dict[str, AreaDetail], start_x: int, start_y: int, mode: str = "side"
):
    """绘制一列深塔（side或center）"""
    col_width = COL_WIDTH

    # 绘制列背景（使用保留的图片）
    bg_path = IMG_CENTER_BG if mode == "center" else IMG_EDGE_BG
    if bg_path.exists():
        col_bg = Image.open(bg_path).convert("RGBA")
        if mode == "side":
            # 侧列降低透明度
            r, g, b, a = col_bg.split()
            a = a.point(lambda p: p * 0.6)
            col_bg = Image.merge("RGBA", (r, g, b, a))
        bg_x = start_x + (col_width - col_bg.width) // 2
        img.paste(col_bg, (bg_x, start_y), col_bg)

    current_y = start_y + 20

    if mode == "center":
        # 中间列：顶部buff（1层buff）、1层、2层、底部buff（3层buff）、3层、4层
        # 顶部buff来自1层
        buffs_1 = []
        if "1" in area_data:
            buffs_1 = [buff.desc for buff in area_data["1"].buffs.values()]
        current_y = await draw_buff_section(img, draw, buffs_1, start_x, current_y)

        # 楼层1
        current_y = await draw_floor_item(img, draw, area_data, "1", 1, start_x, current_y)
        # 楼层2
        current_y = await draw_floor_item(img, draw, area_data, "2", 2, start_x, current_y)

        # 底部buff来自3层
        buffs_3 = []
        if "3" in area_data:
            buffs_3 = [buff.desc for buff in area_data["3"].buffs.values()]
        current_y = await draw_buff_section(img, draw, buffs_3, start_x, current_y)

        # 楼层3
        current_y = await draw_floor_item(img, draw, area_data, "3", 3, start_x, current_y)
        # 楼层4
        current_y = await draw_floor_item(img, draw, area_data, "4", 4, start_x, current_y)
    else:
        # 侧列：顶部buff（取第一个楼层的buff）、楼层1-4
        buffs = []
        sorted_keys = sorted(area_data.keys(), key=lambda x: int(x))
        if sorted_keys:
            first_key = sorted_keys[0]
            buffs = [buff.desc for buff in area_data[first_key].buffs.values()]
        current_y = await draw_buff_section(img, draw, buffs, start_x, current_y)

        # 依次绘制1-4层
        for i in range(1, 5):
            current_y = await draw_floor_item(img, draw, area_data, str(i), i, start_x, current_y)

    return current_y


async def draw_abyss_info_img(param: str = "", mode: str = "tower") -> str | bytes:
    if mode != "tower":
        return "请使用深塔相关指令查看。"

    schedule = await get_tower_schedule()
    if not schedule:
        return "获取深塔排期失败，API可能无法访问。"

    clean_param = param.replace("信息", "").strip()
    season_info = get_target_season_info(schedule, clean_param)

    if not season_info:
        return "未查询到有效的深境之塔排期数据。"

    s_id, s_begin, s_end = season_info
    areas = await get_tower_detail(s_id)
    if not areas:
        return f"获取深塔第 {s_id} 期详情失败。"

    width, height = 3400, 2600
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    if IMG_TOWER_BG.exists():
        bg = Image.open(IMG_TOWER_BG).resize((width, height))
        img.paste(bg, (0, 0))

    draw = ImageDraw.Draw(img)

    title_text = f"逆境深塔 · 第 {s_id} 期"
    date_text = f"{s_begin} ~ {s_end}"

    draw.text((100, 80), title_text, fill="white", font=waves_font_84)
    draw.text((100, 180), date_text, fill=GREY, font=waves_font_42)

    left_area = areas.get("1", {})
    mid_area = areas.get("2", {})
    right_area = areas.get("3", {})

    content_start_y = 240

    await draw_tower_column(img, draw, left_area, start_x=60, start_y=content_start_y, mode="side")
    await draw_tower_column(img, draw, right_area, start_x=2260, start_y=content_start_y, mode="side")
    await draw_tower_column(img, draw, mid_area, start_x=1160, start_y=content_start_y - 190, mode="center")

    img = add_footer(img, 1000, 10, color="encore")
    img = img.resize((2550, 1950))
    return await convert_img(img)
