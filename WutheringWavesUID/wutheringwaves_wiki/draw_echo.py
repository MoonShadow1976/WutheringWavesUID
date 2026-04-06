from pathlib import Path
import re
import textwrap

from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw, ImageFont

from ..utils.ascension.echo import get_echo_model
from ..utils.ascension.model import EchoModel
from ..utils.fonts.waves_fonts import (
    waves_font_30,
    waves_font_40,
    waves_font_origin,
)
from ..utils.image import (
    SPECIAL_GOLD,
    add_footer,
    get_attribute_effect,
    get_crop_waves_bg,
)
from ..utils.name_convert import echo_name_to_echo_id
from ..utils.resource.download_file import get_phantom_img

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


async def parse_echo_base_content(echo_id, echo_model: EchoModel, image, card_img):
    # 提取名称
    echo_name = echo_model.name

    # echo 图片
    echo_pic = await get_phantom_img(echo_id, "")
    echo_pic = crop_center_img(echo_pic, 110, 110)
    echo_pic = echo_pic.resize((250, 250))

    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 20, 330, 380], fill=(0, 0, 0, int(0.4 * 255)))

    image.alpha_composite(echo_pic, (50, 20))

    card_img_draw = ImageDraw.Draw(card_img)
    card_img_draw.text((350, 50), f"{echo_name}", SPECIAL_GOLD, waves_font_40, "lm")

    # 计算echo_name的宽度
    echo_name_width = card_img_draw.textlength(echo_name, waves_font_40) + 350 + 20
    echo_name_width = int(echo_name_width)

    # 合鸣效果
    group_name = echo_model.get_group_name()
    for index, name in enumerate(group_name):
        effect_image = await get_attribute_effect(name)
        effect_image = effect_image.resize((30, 30))
        card_img.alpha_composite(effect_image, (echo_name_width + index * 35, 40))


async def parse_echo_detail_content(echo_model: EchoModel) -> Image.Image:
    """绘制声骸技能描述，返回动态高度的图像。"""
    y_padding = 20  # 初始位移
    line_spacing = 10  # 行间距
    block_line_spacing = 10  # 块行间距
    shadow_radius = 20  # 阴影半径
    padding = 20  # 背景矩形内边距

    title_color = SPECIAL_GOLD
    title_font_size = 20
    title_font = waves_font_origin(title_font_size)

    detail_color = "white"
    detail_font_size = 14
    detail_font = waves_font_origin(detail_font_size)

    title = "技能描述"
    desc = echo_model.get_skill_detail()

    wrapped_title = textwrap.fill(title, width=10)
    wrapped_desc = wrap_text_with_manual_newlines(desc, width=41)

    lines_title = wrapped_title.split("\n")
    lines_desc = wrapped_desc.split("\n")

    # 计算文本总高度（从文本起始点开始累加）
    text_height = (
        len(lines_title) * (title_font_size + line_spacing)
        + len(lines_desc) * (detail_font_size + line_spacing)
        + block_line_spacing
    )

    # 图像内文本起始 Y 坐标（原逻辑保留）
    text_start_y = y_padding + shadow_radius  # 40
    # 图像总高度 = 文本起始Y + 文本高度 + 底部内边距
    img_height = text_start_y + text_height + padding
    img_height = max(img_height, 320)  # 设置一个最小高度

    width = 650
    image = Image.new("RGBA", (width, img_height), (255, 255, 255, 0))
    image_draw = ImageDraw.Draw(image)

    # 绘制背景圆角矩形（边距统一为 padding）
    image_draw.rounded_rectangle(
        [padding, padding, width - padding, img_height - padding],
        radius=20,
        fill=(0, 0, 0, int(0.3 * 255)),
    )

    # 绘制标题
    y_offset = text_start_y
    x_offset = y_padding + shadow_radius  # 40
    for line in lines_title:
        image_draw.text(
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
            image_draw,
            line,
            x_offset,
            y_offset,
            detail_font,
            detail_color,
        )
        y_offset += detail_font.size + line_spacing

    return image


async def parse_echo_statistic_content(echo_model: EchoModel, echo_image):
    rows = echo_model.get_intensity()
    echo_bg = Image.open(TEXT_PATH / "weapon_bg.png")
    echo_bg_temp = Image.new("RGBA", echo_bg.size)
    echo_bg_temp.alpha_composite(echo_bg, dest=(0, 0))
    echo_bg_temp_draw = ImageDraw.Draw(echo_bg_temp)
    for index, row in enumerate(rows):
        echo_bg_temp_draw.text((100, 207 + index * 50), f"{row[0]}", "white", waves_font_30, "lm")
        echo_bg_temp_draw.text((480, 207 + index * 50), f"{row[1]}", "white", waves_font_30, "rm")

    echo_bg_temp = echo_bg_temp.resize((350, 175))
    echo_image.alpha_composite(echo_bg_temp, (10, 200))


async def create_image(echo_id, echo_model: EchoModel):
    detail_image = await parse_echo_detail_content(echo_model)
    H_detail = detail_image.height

    footer_height = 20
    content_bottom = max(400, 80 + H_detail)  # 取 echo_image 底部和 detail 图像底部的最大值
    total_height = max(420, content_bottom + footer_height)  # 保持最小高度 420

    card_img = get_crop_waves_bg(1000, total_height, "bg5")

    echo_image = Image.new("RGBA", (350, 400), (255, 255, 255, 0))
    await parse_echo_base_content(echo_id, echo_model, echo_image, card_img)
    await parse_echo_statistic_content(echo_model, echo_image)

    card_img.alpha_composite(echo_image, (0, 0))
    card_img.alpha_composite(detail_image, (330, 80))

    card_img = add_footer(card_img, 800, footer_height, color="encore")
    card_img = await convert_img(card_img)
    return card_img


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
                    full_tag = segment[1]
                    plain_text = segment[2]
                    text_len = len(plain_text)

                    # 如果加上这个标签会超出宽度，先换行
                    if current_length + text_len > width and current_line:
                        result_lines.append(current_line)
                        current_line = full_tag
                        current_length = text_len
                    else:
                        current_line += full_tag
                        current_length += text_len

            if current_line:
                result_lines.append(current_line)

            wrapped_lines.extend(result_lines)
        else:
            # 没有 color 标签的行正常换行
            wrapped_lines.append(textwrap.fill(line, width=width))

    return "\n".join(wrapped_lines)


async def draw_wiki_echo(echo_name: str):
    echo_id = echo_name_to_echo_id(echo_name)
    if echo_id is None:
        return None

    echo_model: EchoModel | None = get_echo_model(echo_id)
    if not echo_model:
        return f"[鸣潮] 暂无【{echo_name}】对应wiki"

    card_img = await create_image(echo_id, echo_model)
    return card_img
