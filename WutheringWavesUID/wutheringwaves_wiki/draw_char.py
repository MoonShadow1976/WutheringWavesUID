from pathlib import Path
import re
import textwrap

from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw, ImageFont

from ..utils.ascension.char import get_char_model
from ..utils.ascension.model import (
    Chain,
    CharacterModel,
    Skill,
    SkillLevel,
    Stats,
)
from ..utils.fonts.waves_fonts import (
    waves_font_12,
    waves_font_24,
    waves_font_70,
    waves_font_origin,
)
from ..utils.image import (
    GREY,
    SPECIAL_GOLD,
    add_footer,
    get_role_pile,
    get_waves_bg,
)

TEXT_PATH = Path(__file__).parent / "texture2d"

# 颜色标签映射
COLOR_TAG_MAP = {
    "Title": SPECIAL_GOLD,  # 标题
    "Highlight": SPECIAL_GOLD,  # 高亮
    "HighlightB": SPECIAL_GOLD,  # 高亮B
    "Wind": (22, 145, 121),  # 气动 - 啸谷长风
    "Ice": (53, 152, 219),  # 冷凝 - 凝夜白霜
    "Fire": (186, 55, 42),  # 热熔 - 熔山裂谷
    "Thunder": (185, 106, 217),  # 导电 - 彻空冥雷
    "Light": (241, 196, 15),  # 衍射 - 浮星祛暗
    "Dark": (132, 63, 161),  # 湮灭 - 沉日劫明
}


def parse_color_text(text: str) -> list[tuple[str, tuple[int, int, int] | str]]:
    """解析带有 <color> 标签的文本，返回 [(文本片段, 颜色), ...]

    Args:
        text: 包含 <color=XXX>文本</color> 标签的字符串

    Returns:
        列表，每个元素是 (文本内容, 颜色) 的元组
    """
    pattern = r"<color=([^>]+)>([^<]*)</color>"
    result = []
    last_end = 0

    for match in re.finditer(pattern, text):
        # 添加标签前的普通文本
        if match.start() > last_end:
            result.append((text[last_end : match.start()], "white"))

        # 获取颜色和文本
        color_name = match.group(1)
        color_text = match.group(2)
        color = COLOR_TAG_MAP.get(color_name, "white")
        result.append((color_text, color))

        last_end = match.end()

    # 添加最后剩余的普通文本
    if last_end < len(text):
        result.append((text[last_end:], "white"))

    return result if result else [(text, "white")]


def draw_text_with_color(
    draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font: ImageFont.FreeTypeFont, default_color: str | tuple = "white"
) -> int:
    """绘制带有颜色标签的文本

    Args:
        draw: ImageDraw 对象
        text: 包含 <color> 标签的文本
        x: 起始 x 坐标
        y: 起始 y 坐标
        font: 字体
        default_color: 默认颜色

    Returns:
        绘制文本的总宽度
    """
    parsed_text = parse_color_text(text)
    current_x = x

    for text_part, color in parsed_text:
        if not text_part:  # 跳过空字符串
            continue
        draw.text((current_x, y), text_part, font=font, fill=color)
        bbox = draw.textbbox((current_x, y), text_part, font=font)
        current_x = bbox[2]  # 移动到文本末尾

    return int(current_x - x)


async def draw_char_wiki(char_id: str, query_role_type: str):
    if query_role_type == "天赋":
        return await draw_char_skill(char_id)
    elif query_role_type == "命座":
        return await draw_char_chain(char_id)

    return ""


async def draw_char_skill(char_id: str):
    char_model: CharacterModel | None = get_char_model(char_id)
    if char_model is None:
        return ""

    _, char_pile = await get_role_pile(char_id)

    char_pic = char_pile.resize((600, int(600 / char_pile.size[0] * char_pile.size[1])))

    char_bg = Image.open(TEXT_PATH / "title_bg.png")
    char_bg = char_bg.resize((1000, int(1000 / char_bg.size[0] * char_bg.size[1])))
    char_bg_draw = ImageDraw.Draw(char_bg)
    # 名字
    char_bg_draw.text((580, 120), f"{char_model.name}", "black", waves_font_70, "lm")
    # 稀有度
    rarity_pic = Image.open(TEXT_PATH / f"rarity_{char_model.starLevel}.png")
    rarity_pic = rarity_pic.resize((180, int(180 / rarity_pic.size[0] * rarity_pic.size[1])))

    # 90级别数据
    max_stats: Stats = char_model.get_max_level_stat()
    char_stats = await parse_char_stats(max_stats)

    # 技能
    char_skill = await parse_char_skill(char_model.skillTree)

    card_img = get_waves_bg(1000, char_bg.size[1] + char_skill.size[1] + 50, "bg6")

    char_bg.alpha_composite(char_pic, (0, -100))
    char_bg.alpha_composite(char_stats, (580, 340))
    char_bg.alpha_composite(rarity_pic, (560, 160))
    card_img.paste(char_bg, (0, -5), char_bg)
    card_img.alpha_composite(char_skill, (0, 600))

    card_img = add_footer(card_img, 800, 20, color="encore")
    card_img = await convert_img(card_img)
    return card_img


async def draw_char_chain(char_id: str):
    char_model: CharacterModel | None = get_char_model(char_id)
    if char_model is None:
        return ""

    _, char_pile = await get_role_pile(char_id)

    char_pic = char_pile.resize((600, int(600 / char_pile.size[0] * char_pile.size[1])))

    char_bg = Image.open(TEXT_PATH / "title_bg.png")
    char_bg = char_bg.resize((1000, int(1000 / char_bg.size[0] * char_bg.size[1])))
    char_bg_draw = ImageDraw.Draw(char_bg)
    # 名字
    char_bg_draw.text((580, 120), f"{char_model.name}", "black", waves_font_70, "lm")
    # 稀有度
    rarity_pic = Image.open(TEXT_PATH / f"rarity_{char_model.starLevel}.png")
    rarity_pic = rarity_pic.resize((180, int(180 / rarity_pic.size[0] * rarity_pic.size[1])))

    # 90级别数据
    max_stats: Stats = char_model.get_max_level_stat()
    char_stats = await parse_char_stats(max_stats)

    # 命座
    char_chain = await parse_char_chain(char_model.chains)

    card_img = get_waves_bg(1000, char_bg.size[1] + char_chain.size[1] + 50, "bg6")

    char_bg.alpha_composite(char_pic, (0, -100))
    char_bg.alpha_composite(char_stats, (580, 340))
    char_bg.alpha_composite(rarity_pic, (560, 160))
    card_img.paste(char_bg, (0, -5), char_bg)
    card_img.alpha_composite(char_chain, (0, 600))

    card_img = add_footer(card_img, 800, 20, color="encore")
    card_img = await convert_img(card_img)
    return card_img


async def parse_char_stats(max_stats: Stats):
    labels = ["基础生命", "基础攻击", "基础防御"]
    values = [f"{max_stats.life:.0f}", f"{max_stats.atk:.0f}", f"{max_stats.def_:.0f}"]
    rows = [(label, value) for label, value in zip(labels, values)]

    col_count = sum(len(row) for row in rows)
    cell_width = 400
    cell_height = 40
    table_width = cell_width
    table_height = col_count * cell_height

    image = Image.new("RGBA", (table_width, table_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    # 绘制表格
    for row_index, row in enumerate(rows):
        for col_index, cell in enumerate(row):
            # 计算单元格位置
            x0 = col_index * cell_width / 2
            y0 = row_index * cell_height
            x1 = x0 + cell_width / 2
            y1 = y0 + cell_height

            # 绘制矩形边框
            _i = 0.8 if row_index % 2 == 0 else 1
            draw.rectangle([x0, y0, x1, y1], fill=(40, 40, 40, int(_i * 255)), outline=GREY)

            # 计算文本位置以居中
            bbox = draw.textbbox((0, 0), cell, font=waves_font_24)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = x0 + (cell_width / 2 - text_width) / 2
            text_y = y0 + (cell_height - text_height) / 2

            # 绘制文本
            draw.text((text_x, text_y), cell, fill="white", font=waves_font_24)

    return image


async def parse_char_chain(data: dict[int, Chain]):
    y_padding = 20  # 初始位移
    x_padding = 20  # 初始位移
    line_spacing = 10  # 行间距
    block_line_spacing = 50  # 块行间距
    image_width = 1000  # 每个图像的宽度
    shadow_radius = 20  # 阴影半径

    title_color = SPECIAL_GOLD
    title_font_size = 40
    title_font = waves_font_origin(title_font_size)

    detail_color = "white"
    detail_color_size = 30
    detail_font = waves_font_origin(detail_color_size)

    images = []
    for chain_num in data:
        item = data[chain_num]
        # 拼接文本
        title = item.name
        desc = item.get_desc_detail()

        # 分行显示标题
        wrapped_title = textwrap.fill(title, width=20)
        wrapped_desc = wrap_text_with_manual_newlines(desc, width=31)

        # 获取每行的宽度，确保不会超过设定的 image_width
        lines_title = wrapped_title.split("\n")
        lines_desc = wrapped_desc.split("\n")

        # 计算总的绘制高度
        total_text_height = y_padding + block_line_spacing + shadow_radius * 2
        total_text_height += len(lines_title) * (title_font_size + line_spacing)  # 标题部分的总高度
        total_text_height += len(lines_desc) * (detail_color_size + line_spacing)  # 描述部分的总高度

        img = Image.new(
            "RGBA",
            (image_width, total_text_height),
            color=(255, 255, 255, 0),
        )
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [
                shadow_radius,
                shadow_radius,
                image_width - shadow_radius,
                total_text_height - shadow_radius,
            ],
            fill=(0, 0, 0, int(0.3 * 255)),
        )

        # 绘制标题文本
        y_offset = y_padding + shadow_radius
        x_offset = x_padding + shadow_radius
        for line in lines_title:
            draw.text(
                (x_offset, y_offset),
                line,
                font=title_font,
                fill=title_color,
            )
            y_offset += int(title_font.size) + line_spacing

        y_offset += block_line_spacing

        # 绘制描述文本
        for line in lines_desc:
            draw_text_with_color(
                draw,
                line,
                x_offset,
                y_offset,
                detail_font,
                detail_color,
            )
            y_offset += detail_font.size + line_spacing

        images.append(img)

    # 拼接所有图像
    total_height = sum(img.height for img in images)
    final_img = Image.new("RGBA", (image_width, total_height), color=(255, 255, 255, 0))

    y_offset = 0
    for img in images:
        final_img.paste(img, (0, y_offset))
        y_offset += img.height

    return final_img


async def parse_char_skill(data: dict[str, dict[str, Skill]]):
    y_padding = 20  # 初始位移
    x_padding = 20  # 初始位移
    line_spacing = 10  # 行间距
    block_line_spacing = 20  # 块行间距
    image_width = 1000  # 每个图像的宽度
    shadow_radius = 20  # 阴影半径

    title_color = SPECIAL_GOLD
    title_font_size = 30
    title_font = waves_font_origin(title_font_size)

    detail_color = "white"
    detail_color_size = 14
    detail_font = waves_font_origin(detail_color_size)

    keys = [
        ("常态攻击", "1", ["12", "13"]),
        ("共鸣技能", "2", ["10", "14"]),
        ("共鸣回路", "7", ["4", "5"]),
        ("共鸣解放", "3", ["11", "15"]),
        ("变奏技能", "6", ["9", "16"]),
        ("谐度破坏", "17", []),
        ("延奏技能", "8", []),
    ]

    images = []
    for skill_type, skill_tree_id, relate_skill_tree_ids in keys:
        item = data[skill_tree_id]["skill"]

        # 拼接文本
        title = skill_type
        desc = item.get_desc_detail()

        # 分行显示标题
        wrapped_title = textwrap.fill(title, width=10)
        wrapped_desc = wrap_text_with_manual_newlines(desc, width=65)

        # 获取每行的宽度，确保不会超过设定的 image_width
        lines_title = wrapped_title.split("\n")
        lines_desc = wrapped_desc.split("\n")

        for relate_id in relate_skill_tree_ids:
            relate_item = data[relate_id]["skill"]
            _type = relate_item.type if relate_item.type else "属性加成"
            relate_title = f"{_type}: {relate_item.name}"
            relate_desc = relate_item.get_desc_detail()
            wrapped_relate_desc = wrap_text_with_manual_newlines(relate_desc, width=65)

            lines_desc.append(relate_title)
            lines_desc.extend(wrapped_relate_desc.split("\n"))

        # 计算总的绘制高度
        total_text_height = y_padding + block_line_spacing + shadow_radius * 2
        total_text_height += len(lines_title) * (title_font_size + line_spacing)  # 标题部分的总高度
        total_text_height += len(lines_desc) * (detail_color_size + line_spacing)  # 描述部分的总高度

        img = Image.new(
            "RGBA",
            (image_width, total_text_height),
            color=(255, 255, 255, 0),
        )
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [
                shadow_radius,
                shadow_radius,
                image_width - shadow_radius,
                total_text_height - shadow_radius,
            ],
            fill=(0, 0, 0, int(0.3 * 255)),
        )

        # 绘制标题文本
        y_offset = y_padding + shadow_radius
        x_offset = x_padding + shadow_radius
        for line in lines_title:
            draw.text(
                (x_offset, y_offset),
                line,
                font=title_font,
                fill=title_color,
            )
            y_offset += int(title_font.size) + line_spacing

        y_offset += block_line_spacing

        # 绘制描述文本
        for line in lines_desc:
            color = title_color if line.startswith("属性加成") or line.startswith("固有技能") else detail_color
            draw_text_with_color(
                draw,
                line,
                x_offset,
                y_offset,
                detail_font,
                color,
            )
            y_offset += detail_font.size + line_spacing

        images.append(img)

        skill_rate = await parse_char_skill_rate(item.level)
        if skill_rate:
            images.append(skill_rate)

    # 拼接所有图像
    total_height = sum(img.height for img in images)
    final_img = Image.new("RGBA", (image_width, total_height), color=(255, 255, 255, 0))

    y_offset = 0
    for img in images:
        final_img.paste(img, (0, y_offset))
        y_offset += img.height

    return final_img


async def parse_char_skill_rate(skillLevels: dict[str, SkillLevel] | None):
    if not skillLevels:
        return
    rows = []
    labels = [
        "等级",
        "Lv 6",
        "Lv 7",
        "Lv 8",
        "Lv 9",
        "Lv 10",
    ]
    rows.append(labels)

    for _, skillLevel in skillLevels.items():
        row = [skillLevel.name]
        row.extend(skillLevel.param[0][5:10])
        rows.append(row)

    font = waves_font_12
    offset = 20
    col_count = len(rows)
    cell_width = 155
    first_col_width = cell_width + 50
    cell_height = 40
    table_width = 1000
    table_height = col_count * cell_height

    image = Image.new("RGBA", (table_width, table_height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    # 绘制表格
    for row_index, row in enumerate(rows):
        for col_index, cell in enumerate(row):
            # 计算单元格位置
            if col_index == 0:
                x0 = offset
                x1 = first_col_width
            else:
                x0 = first_col_width + (col_index - 1) * cell_width
                x1 = x0 + cell_width

            y0 = row_index * cell_height
            y1 = y0 + cell_height

            # 绘制矩形边框
            _i = 0.3 if row_index % 2 == 0 else 0.7
            draw.rectangle([x0, y0, x1, y1], fill=(40, 40, 40, int(_i * 255)), outline=GREY)

            # 计算文本位置以居中
            bbox = draw.textbbox((0, 0), cell, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            if col_index == 0:
                text_x = (x0 + first_col_width - text_width) / 2
            else:
                text_x = x0 + (cell_width - text_width) / 2
            text_y = y0 + (cell_height - text_height) / 2

            # 绘制文本
            wrapped_cell = textwrap.wrap(cell, width=18)
            if len(wrapped_cell) > 1:
                text_y_temp = text_y - font.size
                for line in wrapped_cell:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    if col_index == 0:
                        text_x = (x0 + first_col_width - text_width) / 2
                    else:
                        text_x = x0 + (cell_width - text_width) / 2
                    draw.text(
                        (text_x, text_y_temp),
                        line,
                        fill="white",
                        font=font,
                    )
                    text_y_temp += font.size + 7
            else:
                draw.text(
                    (text_x, text_y),
                    cell,
                    fill="white",
                    font=font,
                )

    return image


def wrap_text_with_manual_newlines(
    text: str,
    width: int = 70,
) -> str:
    """
    处理文本，优先保留原始文本中的 \n，再使用 textwrap 进行换行。
    对包含 <color> 标签的文本进行智能换行，保持标签完整。

    :param text: 原始文本
    :param width: 自动换行的宽度
    :return: 处理后的文本
    """
    lines = text.split("\n")
    wrapped_lines = []

    for line in lines:
        # 如果这行包含 color 标签，需要特殊处理
        if "<color=" in line:
            # 将行分割成带标签和不带标签的片段
            segments = []
            last_end = 0

            for match in re.finditer(r"<color=([^>]+)>([^<]*)</color>", line):
                # 添加标签前的文本
                if match.start() > last_end:
                    segments.append(("plain", line[last_end : match.start()]))
                # 添加带标签的文本（作为一个整体）
                segments.append(("colored", match.group(0), match.group(2)))
                last_end = match.end()

            # 添加最后剩余的文本
            if last_end < len(line):
                segments.append(("plain", line[last_end:]))

            # 手动换行，保持标签完整，按字符处理
            current_line = ""
            current_length = 0
            result_lines = []

            for segment in segments:
                if segment[0] == "plain":
                    text_part = segment[1]
                    # 对纯文本按字符进行换行
                    for char in text_part:
                        if current_length >= width:
                            result_lines.append(current_line)
                            current_line = char
                            current_length = 1
                        else:
                            current_line += char
                            current_length += 1
                elif segment[0] == "colored":
                    color_name = re.search(r"<color=([^>]+)>", segment[1]).group(1)
                    plain_text = segment[2]
                    in_color_tag = False

                    # 对彩色文本也按字符进行换行
                    for i, char in enumerate(plain_text):
                        if current_length >= width:
                            # 如果当前在颜色标签内，先关闭标签
                            if in_color_tag:
                                current_line += "</color>"
                                in_color_tag = False
                            result_lines.append(current_line)
                            # 新行开始，添加颜色标签
                            current_line = f"<color={color_name}>{char}"
                            current_length = 1
                            in_color_tag = True
                        else:
                            # 如果是第一个字符，需要开启标签
                            if not in_color_tag:
                                current_line += f"<color={color_name}>"
                                in_color_tag = True
                            current_line += char
                            current_length += 1

                    # 关闭颜色标签
                    if in_color_tag:
                        current_line += "</color>"

            if current_line:
                result_lines.append(current_line)

            wrapped_lines.extend(result_lines)
        else:
            # 没有 color 标签的行正常换行
            wrapped_lines.append(textwrap.fill(line, width=width))

    return "\n".join(wrapped_lines)
