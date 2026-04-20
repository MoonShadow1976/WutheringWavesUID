from pathlib import Path
import re

import aiohttp
from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw
from pydantic import BaseModel

from ..utils.ascension.monster import get_all_monster_models
from ..utils.fonts.waves_fonts import (
    waves_font_20,
    waves_font_32,
    waves_font_84,
)
from ..utils.image import (
    add_footer,
    get_square_avatar,
    pic_download_from_url,
)
from ..utils.resource.RESOURCE_PATH import MATRIX_PATH

# 路径配置
TEXT_PATH = Path(__file__).parent / "texture2d"
all_monster = get_all_monster_models()
# 颜色映射

# 常量
CARD_WIDTH = 1520
CARD_PADDING = 20
CORNER_RADIUS = 15
BG_COLOR = (80, 80, 80, 100)

MONSTER_CARD_WIDTH = 340
MONSTER_GRID_COLS = 2
MONSTER_GRID_SPACING = 10

# 字体
FONT_TITLE = waves_font_32
FONT_DESC = waves_font_20
FONT_MONSTER_NAME = waves_font_20
FONT_BUFF = waves_font_20
FONT_ITEM_NAME = waves_font_20

BUFF_LINE_SPACING = 20
BUFF_PADDING = 15
DESC_LINE_SPACING = 20

URL = "https://api-v2.encore.moe/api/zh-Hans/dpmatrix"


# ---------- 数据模型 ----------
class Tag(BaseModel):
    Id: int
    Name: str
    Desc: str
    Path: str
    Color: str


class ShowBuff(BaseModel):
    Id: int
    SkillBgQuality: str
    SkillIconBgQuality: str
    DetailTipBgQuality: str
    SkillIcon: str
    SmallIcon: str
    BuffColor: str
    SkillTitle: str
    SkillDesc: str


class RecommendTeamFeature(BaseModel):
    Id: int
    Icon: str
    Name: str


class Wave(BaseModel):
    Id: int
    Level: int
    Round: int
    Wave: int
    RecommendId: int
    KillScore: int
    MonsterLevel: int
    MonsterId: int
    Icon: str
    Name: str
    Desc: str
    SmallIcon: str
    BigIcon: list[str]
    TagIdList: list[int]
    SmallIconInModeView: str
    BigIconInModeView: str
    SmallIconHandBook: str
    MonsterPortrait: str
    ElementId: int
    ShowBuffIds: list[ShowBuff]
    HandBookBuff: list[dict]
    RecommendTeamFeature: list[RecommendTeamFeature]
    LevelId: int
    Tags: list[Tag] = []


class Buff(BaseModel):
    Id: int
    Icon: str
    Name: str
    Desc: str


class ScoreLevelRule(BaseModel):
    Key: int
    Value: int
    Icon: str
    IconSettlement: str
    BgColor: str
    SquareColor: str
    CircleColor: str
    GridColor: str
    BgLightColor: str
    TextColor: str


class LimitParam(BaseModel):
    Key: str
    Value: str


class CondDetail(BaseModel):
    Id: int
    Type: str
    NeedNum: int
    LimitParams: list[LimitParam]
    Description: str


class LevelDetail(BaseModel):
    Id: int
    Param: int
    InstId: int
    Cond: int | CondDetail | None = None
    MaxLoopCount: int
    TeamLimit: int
    Diff: int
    NewTowerBuffs: list[Buff]
    NewTowerBuffCount: int
    ScoreLevelRule: list[ScoreLevelRule]
    Name: str
    Waves: list[Wave]


class EnhanceSkillDescItem(BaseModel):
    Key: int
    Value: str


class RoleInfo(BaseModel):
    QualityId: int
    Name: str
    ElementId: int
    RoleHeadIconCircle: str
    RoleHeadIconLarge: str
    RoleHeadIconBig: str
    RoleHeadIcon: str
    WeaponType: int


class Role(BaseModel):
    Id: int
    AddBuffs: list[dict]
    TemplateRoleId: int
    EnhanceSkillDesc: list[EnhanceSkillDescItem]
    EnhanceSkillDescParam: list[dict]
    TemplateDesc: str
    RoleInfo: RoleInfo


class MatrixDetailResponse(BaseModel):
    Season: int
    Name: str
    LevelIds: list[int]
    Levels: list[LevelDetail]
    Roles: list[Role]


# ---------- 辅助函数 ----------
def parse_and_wrap_text(text: str, max_chars_per_line: int = 31) -> list[list[tuple[str, str]]]:
    """解析带颜色标签的文本，返回按行分割的颜色片段列表"""
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
    line_spacing = 20
    curr_y = start_y
    for line in lines:
        curr_x = start_x
        for text, color_key in line:
            if color_key.startswith("#"):
                fill_color = color_key
            else:
                fill_color = color_key
            draw.text((curr_x, curr_y), text, fill=fill_color, font=font)
            curr_x += font.getlength(text)
        curr_y += line_spacing


def draw_rounded_rect(img: Image.Image, xy, radius, color):
    """叠加半透明圆角矩形"""
    x1, y1, x2, y2 = xy
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=color)
    img.alpha_composite(layer, (0, 0))


async def get_matrix_schedule() -> list[int]:
    """获取矩阵所有赛季ID列表"""
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
    seasons = [item["Season"] for item in data]
    return sorted(seasons)


async def get_matrix_detail(season_id: str) -> MatrixDetailResponse | None:
    """获取单期矩阵详情"""
    url = f"{URL}/{season_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
    return MatrixDetailResponse.model_validate(data)


def get_target_season_info(season_ids: list[int], param: str = "") -> int | None:
    """根据参数确定目标赛季ID"""
    if not season_ids:
        return None
    if param and param.isdigit():
        target = int(param)
        if target in season_ids:
            return target
        return None
    if param in ["下期", "下", "next"]:
        return max(season_ids)
    return max(season_ids) - 1


def parse_color(color_str: str) -> str:
    """将 '55ffb5ff' 或 '#55ffb5' 转换为 '#55ffb5' 格式"""
    if not color_str:
        return "white"
    color_str = color_str.lstrip("#")
    if len(color_str) >= 6:
        return f"#{color_str[:6]}"
    return "white"


# ---------- 辅助函数（新增） ----------
def draw_rounded_rect_on_image(img: Image.Image, xy, radius, color):
    """在原地绘制半透明圆角矩形（用于已有图像）"""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.rounded_rectangle(xy, radius=radius, fill=color)
    img.alpha_composite(layer, (0, 0))


# ---------- 各组件绘制函数（返回 Image） ----------
async def draw_buff_section(
    buffs: list[Buff],
    width: int,
) -> Image.Image | None:
    """绘制全局Buff区域，返回图像"""
    if not buffs:
        return None

    icon_size = 40
    line_height = BUFF_LINE_SPACING  # 固定行距
    padding = BUFF_PADDING

    # 预计算每个 buff 的行数和所需高度
    buff_heights = []
    buff_line_counts = []
    for buff in buffs:
        lines = parse_and_wrap_text(buff.Desc, max_chars_per_line=70)
        line_count = len(lines)
        text_height = line_count * line_height
        buff_height = max(icon_size, text_height) // 4 * 5
        buff_heights.append(buff_height)
        buff_line_counts.append((lines, line_count))

    total_height = sum(buff_heights) + 2 * padding  # 缓冲之间加间距
    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
    draw_rounded_rect_on_image(img, (0, 0, width, total_height), CORNER_RADIUS, BG_COLOR)

    draw = ImageDraw.Draw(img)
    curr_y = padding

    for buff, (lines, line_count), buff_h in zip(buffs, buff_line_counts, buff_heights):
        # 图标绘制位置：左侧，垂直居中于该 buff 区域
        icon_y = curr_y + (buff_h - icon_size) // 2
        icon_img = await pic_download_from_url(MATRIX_PATH, buff.Icon)
        icon_img = icon_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        img.paste(icon_img, (padding, icon_y), icon_img)

        # 文字起始 X
        text_x = padding + icon_size + 10
        # 文字起始 Y：该 buff 区域的顶部 + 内边距
        text_y = curr_y + (buff_h - icon_size)
        for line in lines:
            draw_colored_lines(draw, [line], text_x, text_y, FONT_BUFF)
            text_y += line_height

        # 移动到下一个 buff 区域
        curr_y += buff_h

    return img


async def draw_wave_card(
    monster_id: int,
    waves: list[Wave],
    width: int,
) -> Image.Image | None:
    if not waves:
        return None

    template = waves[0]
    max_level = max(w.MonsterLevel for w in waves)

    # 下载所有需要的图片资源（异步并行）
    bg_icon = await pic_download_from_url(MATRIX_PATH, template.Icon)
    bg_icon = bg_icon.convert("RGBA")
    icon_width = width - 2 * CARD_PADDING
    bg_icon = bg_icon.resize((icon_width, int(icon_width * bg_icon.height / bg_icon.width)), Image.Resampling.LANCZOS)
    bg_icon_height = bg_icon.height

    # 收集唯一描述和 Buff
    unique_descs = []
    seen_desc = set()
    for w in waves:
        if w.Desc.strip() and w.Desc.strip() not in seen_desc:
            seen_desc.add(w.Desc.strip())
            unique_descs.append(w.Desc.strip())

    unique_buffs = {}
    for w in waves:
        for buff in w.ShowBuffIds:
            if buff.Id not in unique_buffs:
                unique_buffs[buff.Id] = buff

    recommend_features = template.RecommendTeamFeature

    # 预下载所有技能图标和角色图标
    skill_icons = {}
    for buff in unique_buffs.values():
        icon = await pic_download_from_url(MATRIX_PATH, buff.SkillIcon)
        skill_icons[buff.Id] = icon.resize((32, 32), Image.Resampling.LANCZOS)

    role_icons = {}
    icon_size = 50
    for recom in recommend_features:
        icon = await pic_download_from_url(MATRIX_PATH, recom.Icon)
        role_icons[recom.Id] = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)

    # 辅助函数：测量文本块的总高度（像素）
    def measure_text_block(lines: list[list[tuple[str, str]]], font, line_spacing=20) -> int:
        # 每行高度为 line_spacing，不考虑字体实际高度（保持简单）
        return len(lines) * line_spacing

    # 收集所有文本行
    desc_lines_list = []
    for desc in unique_descs:
        lines = parse_and_wrap_text(desc, max_chars_per_line=34)
        desc_lines_list.append(lines)

    buff_lines_list = []
    for buff in unique_buffs.values():
        title_lines = [[(buff.SkillTitle, parse_color(buff.BuffColor))]]  # 标题作为一行（带颜色）
        desc_lines = parse_and_wrap_text(buff.SkillDesc, max_chars_per_line=32)
        buff_lines_list.append((title_lines, desc_lines))

    # 计算高度
    name_height = 30
    tag_height = 30 if template.Tags else 0
    # 背景图标下方开始内容
    content_start_y = CARD_PADDING + bg_icon_height

    curr_y = content_start_y
    # 描述
    for lines in desc_lines_list:
        curr_y += measure_text_block(lines, FONT_DESC) + BUFF_LINE_SPACING  # + 空行间距
    # Buff
    for title_lines, desc_lines in buff_lines_list:
        curr_y += measure_text_block(title_lines, FONT_BUFF) + BUFF_LINE_SPACING
        curr_y += measure_text_block(desc_lines, FONT_DESC) + BUFF_LINE_SPACING

    # ========== 动态计算推荐体系布局 ==========
    icon_text_gap = 5
    available_width = width - 2 * CARD_PADDING
    if recommend_features:
        # 计算每个条目的宽度（图标 + 间隙 + 文本宽度）
        item_widths = []
        for recom in recommend_features:
            text_width = FONT_ITEM_NAME.getlength(recom.Name)
            item_width = icon_size + icon_text_gap + text_width
            item_widths.append(item_width)

        # 动态换行：计算每行放哪些条目
        rows = []
        current_row = []
        current_row_width = 0
        for idx, w in enumerate(item_widths):
            needed = w + (0 if not current_row else BUFF_LINE_SPACING)
            if current_row_width + needed <= available_width:
                current_row.append(idx)
                current_row_width += needed
            else:
                if current_row:
                    rows.append(current_row)
                current_row = [idx]
                current_row_width = w
        if current_row:
            rows.append(current_row)

        num_rows = len(rows)
        recommend_height = num_rows * (icon_size + BUFF_LINE_SPACING // 2) + BUFF_LINE_SPACING // 2
        curr_y += recommend_height
    else:
        recommend_height = 0

    total_height = curr_y + CARD_PADDING

    # 创建最终图像
    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 100))
    draw_rounded_rect_on_image(img, (0, 0, width, total_height), CORNER_RADIUS, BG_COLOR)

    # 背景半透明叠加
    bg_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bg_layer.paste(bg_icon, (CARD_PADDING, CARD_PADDING), bg_icon)
    img.alpha_composite(bg_layer, (0, 0))

    draw = ImageDraw.Draw(img)

    # 名称和等级
    name_text = f"{template.Name}  Lv.{max_level}"
    draw.text((CARD_PADDING, CARD_PADDING + 20), name_text, fill="white", font=FONT_MONSTER_NAME)

    # Tags
    if template.Tags:
        tag_x = CARD_PADDING
        tag_y = CARD_PADDING + 20 + name_height
        for tag in template.Tags:
            color = parse_color(tag.Color)
            draw.text((tag_x, tag_y), tag.Name, fill=color, font=FONT_ITEM_NAME)
            tag_x += FONT_ITEM_NAME.getlength(tag.Name) + 20

    curr_y = content_start_y

    # 绘制描述
    for lines in desc_lines_list:
        draw_colored_lines(draw, lines, CARD_PADDING, curr_y, FONT_DESC)
        curr_y += measure_text_block(lines, FONT_DESC) + BUFF_LINE_SPACING

    # 绘制 Buff
    icon_small = 32
    for buff, (title_lines, desc_lines) in zip(unique_buffs.values(), buff_lines_list):
        # 技能图标
        skill_icon = skill_icons[buff.Id]
        img.paste(skill_icon, (CARD_PADDING, curr_y), skill_icon)
        # 标题
        title_color = parse_color(buff.BuffColor)
        title_x = CARD_PADDING + icon_small + 10
        for line in title_lines:
            draw_colored_lines(draw, [line], title_x, curr_y, FONT_BUFF)
        curr_y += measure_text_block(title_lines, FONT_BUFF) + BUFF_LINE_SPACING
        # 描述
        for line in desc_lines:
            draw_colored_lines(draw, [line], title_x, curr_y, FONT_DESC)
            curr_y += BUFF_LINE_SPACING
        curr_y += BUFF_LINE_SPACING

    # ========== 绘制推荐体系（动态布局） ==========
    if recommend_features:
        role_start_y = curr_y + BUFF_LINE_SPACING
        for row_idx, row_indices in enumerate(rows):
            row_y = role_start_y + row_idx * (icon_size + BUFF_LINE_SPACING // 2)
            x_offset = CARD_PADDING
            for idx in row_indices:
                recom = recommend_features[idx]
                role_icon = role_icons[recom.Id]
                img.paste(role_icon, (x_offset, row_y), role_icon)
                text_y = row_y + icon_size // 4  # 保持与原逻辑一致的垂直偏移
                draw.text((x_offset + icon_size + icon_text_gap, text_y), recom.Name, fill="white", font=FONT_ITEM_NAME)
                # 计算当前条目实际宽度用于下一个x偏移
                item_width = icon_size + icon_text_gap + FONT_ITEM_NAME.getlength(recom.Name)
                x_offset += int(item_width) + BUFF_LINE_SPACING

    return img


async def draw_roles_section(
    roles: list[Role],
    width: int,
) -> Image.Image | None:
    """绘制角色区域，每个卡片左侧图标右侧描述，返回图像"""
    if not roles:
        return None

    # 先计算每个卡片的高度（动态）
    card_heights = []
    card_widths = []  # 每个卡片宽度（固定）
    role_card_width = (width - 100) // 4  # 4列
    role_icon_size = 80

    for role in roles:
        # 计算右侧描述文本行数
        desc_lines_total = 0
        for desc in role.EnhanceSkillDesc:
            lines = parse_and_wrap_text(desc.Value, max_chars_per_line=12)  # 根据卡片宽度调整
            desc_lines_total += len(lines)
        # 卡片高度 = max(图标高度, 描述总高度) + 内边距
        desc_height = desc_lines_total * 20 + 20  # 行高20，额外内边距
        h = max(role_icon_size + 20, desc_height) + 20
        card_heights.append(h)

    # 布局：每行4个，行高取本行最大卡片高度
    rows = []
    for i in range(0, len(roles), 4):
        row_roles = roles[i : i + 4]
        row_heights = card_heights[i : i + 4]
        row_height = max(row_heights) + 20  # 行间距
        rows.append((row_roles, row_height))

    total_height = sum(h for _, h in rows) + 60  # 标题区域高度

    # 创建关卡画布
    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
    draw_rounded_rect_on_image(img, (0, 0, width, total_height), CORNER_RADIUS, BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 绘制标题（可选）
    draw.text((20, 20), "助力角色", fill="white", font=FONT_TITLE)

    curr_y = 60
    for row_roles, row_height in rows:
        row_start_y = curr_y
        # 本行内每个卡片按自己的高度绘制
        for col, role in enumerate(row_roles):
            idx = (curr_y - 60) // (row_height) * 4 + col
            card_h = card_heights[idx]
            rx = 20 + col * (role_card_width + 20)
            ry = row_start_y
            # 绘制卡片背景
            draw_rounded_rect_on_image(img, (rx, ry, rx + role_card_width, ry + card_h), CORNER_RADIUS, BG_COLOR)

            # 左侧图标（垂直居中）
            icon_y = ry + (card_h - role_icon_size) // 4
            role_icon = await get_square_avatar(role.Id)
            role_icon = role_icon.resize((role_icon_size, role_icon_size), Image.Resampling.LANCZOS)
            img.paste(role_icon, (rx + 10, icon_y), role_icon)

            # 右侧描述文本
            text_x = rx + role_icon_size + 20
            text_y = ry + 15
            for desc in role.EnhanceSkillDesc:
                lines = parse_and_wrap_text(desc.Value, max_chars_per_line=12)
                for line in lines:
                    draw_colored_lines(draw, [line], text_x, text_y, FONT_DESC)
                    text_y += 20
            # 角色名显示在图标下方或描述区？按需求放在图标下方居中
            name_x = rx + role_icon_size // 2 + 10
            name_y = icon_y + role_icon_size + 5
            draw.text((name_x, name_y), role.RoleInfo.Name, fill="white", font=FONT_ITEM_NAME, anchor="ma")
        curr_y += row_height

    return img


async def draw_level_card(level: LevelDetail, width: int) -> Image.Image:
    # 按怪物 ID 分组
    waves_by_monster = {}
    ordered_mids = []
    seen = set()
    for wave in level.Waves:
        mid = wave.MonsterId
        if mid not in seen:
            seen.add(mid)
            ordered_mids.append(mid)
        if mid not in waves_by_monster:
            waves_by_monster[mid] = []
        waves_by_monster[mid].append(wave)

    # 并行生成所有怪物卡片图像
    monster_card_width = (width - 100 - MONSTER_GRID_SPACING) // 2
    monster_cards = []
    for mid in ordered_mids:
        card_img = await draw_wave_card(mid, waves_by_monster[mid], monster_card_width)
        monster_cards.append(card_img)

    # 计算网格行布局（两列，动态行高）
    rows = []
    for i in range(0, len(monster_cards), 2):
        left = monster_cards[i]
        right = monster_cards[i + 1] if i + 1 < len(monster_cards) else None
        row_height = max(left.height, right.height if right else 0) + MONSTER_GRID_SPACING
        rows.append((left, right, row_height))

    # 生成 Buff 图像
    buff_img = await draw_buff_section(level.NewTowerBuffs, width - 100)

    # 计算总高度
    total_height = 60  # 标题区域
    if buff_img:
        total_height += buff_img.height + CARD_PADDING
    total_height += sum(row[2] for row in rows) + 2 * CARD_PADDING

    # 创建关卡画布
    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
    draw_rounded_rect_on_image(img, (0, 0, width, total_height), CORNER_RADIUS, BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 标题
    draw.text((50, 20), "敌人信息", fill="white", font=FONT_TITLE)

    curr_y = 60
    if buff_img:
        img.paste(buff_img, (50, curr_y), buff_img)
        curr_y += buff_img.height + CARD_PADDING

    # 粘贴怪物卡片
    for left, right, row_height in rows:
        if left:
            img.paste(left, (50, curr_y), left)
        if right:
            img.paste(right, (50 + monster_card_width + MONSTER_GRID_SPACING, curr_y), right)
        curr_y += row_height

    return img


async def draw_matrix_info_img(param: str = "", mode: str = "matrix") -> str | bytes:
    if mode != "matrix":
        return "请使用深塔相关指令查看。"

    season_ids = await get_matrix_schedule()
    if not season_ids:
        return "获取深塔排期失败，API可能无法访问。"

    clean_param = param.replace("信息", "").strip()
    target_season = get_target_season_info(season_ids, clean_param)
    if target_season is None:
        return "未查询到有效的深塔赛季。"

    detail = await get_matrix_detail(str(target_season))
    if not detail:
        return f"获取深塔第 {target_season} 期详情失败。"

    target_levels = [lvl for lvl in detail.Levels if lvl.Name == "奇点扩张"]
    if not target_levels:
        target_levels = detail.Levels

    # 生成角色图像
    roles_img = await draw_roles_section(detail.Roles, CARD_WIDTH)
    # 生成关卡图像列表
    level_imgs = [await draw_level_card(lvl, CARD_WIDTH) for lvl in target_levels]

    # 动态计算总高度
    total_height = 240  # 顶部标题区域
    if roles_img:
        total_height += roles_img.height + 40
    for lvl_img in level_imgs:
        total_height += lvl_img.height + CARD_PADDING
    total_height += 100

    width = CARD_WIDTH + 180
    bg_img = Image.new("RGBA", (width, total_height), (0, 0, 0, 255))

    # 可选背景图
    bg_path = TEXT_PATH / "matrix_bg.png"
    if bg_path.exists():
        bg = Image.open(bg_path).convert("RGBA")
        bgwidth = width * (bg.height / total_height)
        bg = bg.crop(((bg.width - bgwidth) // 2, 0, (bg.width + bgwidth) // 2, bg.height))
        bg = bg.resize((width, total_height), Image.Resampling.LANCZOS)
        dark_overlay = Image.new("RGBA", bg.size, (0, 0, 0, 128))  # 50% 透明度黑色
        bg = Image.alpha_composite(bg, dark_overlay)
        bg_img.paste(bg, (0, 0), bg)
    else:
        bg_img.paste((10, 10, 20, 255), (0, 0, width, total_height))

    draw = ImageDraw.Draw(bg_img)

    # 标题
    title_text = f"第 {target_season} 期 · 矩阵 · {detail.Name}"
    draw.text((100, 80), title_text, fill="white", font=waves_font_84)

    current_y = 240
    if roles_img:
        offset_x = (width - roles_img.width) // 2
        bg_img.paste(roles_img, (offset_x, current_y), roles_img)
        current_y += roles_img.height + 40
    for lvl_img in level_imgs:
        offset_x = (width - lvl_img.width) // 2
        bg_img.paste(lvl_img, (offset_x, current_y), lvl_img)
        current_y += lvl_img.height + CARD_PADDING

    # 裁剪到实际内容区域
    final_img = bg_img.crop((0, 0, width, current_y + 50))
    final_img = add_footer(final_img, 1000, 10, color="encore")
    final_img = final_img.resize((int(width * 0.75), int((current_y + 50) * 0.75)), Image.Resampling.LANCZOS)
    return await convert_img(final_img)
