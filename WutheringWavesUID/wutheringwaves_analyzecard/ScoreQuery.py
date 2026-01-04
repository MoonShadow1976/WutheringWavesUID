# change from https://github.com/alone-art/ScoreQuery

from pathlib import Path
import re

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw

from ..utils.api.model import (
    Props,
)
from ..utils.ascension.char import get_char_model
from ..utils.calculate import (
    calc_phantom_entry,
    calc_phantom_score,
    get_calc_map,
    get_valid_color,
)
from ..utils.fonts.waves_fonts import (
    waves_font_18,
    waves_font_24,
    waves_font_36,
)
from ..utils.image import (
    add_footer,
    get_attribute_prop,
    get_role_pile,
    get_square_avatar,
)
from ..utils.name_convert import alias_to_char_name, char_name_to_char_id
from .ocrspace import get_upload_img, ocrspace

TEXT_PATH = Path(__file__).parent / "texture2d"

# fmt: off
valid_keys = [
    "小生命", "生命",
    "小攻击", "攻击",
    "小防御", "防御",
    "共鸣效率",
    "暴击伤害", "暴击",
    "普攻伤害加成",
    "重击伤害加成",
    "共鸣技能伤害加成",
    "共鸣解放伤害加成",
    "气动伤害加成",
    "冷凝伤害加成",
    "导电伤害加成",
    "衍射伤害加成",
    "湮灭伤害加成",
    "热熔伤害加成",
    "治疗效果加成",
]

valid_values = [
    "320", "360", "390", "430", "470", "510", "540", "580",
    "30", "40", "50", "60",
    "70",
    "6.0%", "6.4%", "7.1%", "7.9%", "8.6%", "9.4%", "10.1%", "10.9%", "11.6%",
    "8.1%", "9.0%", "10.0%", "10.9%", "11.8%", "12.8%", "13.8%", "14.7%",
    "6.8%", "7.6%", "8.4%", "9.2%", "10.0%", "10.8%", "11.6%", "12.4%",
    "6.3%", "6.9%", "7.5%", "8.1%", "8.7%", "9.3%", "9.9%", "10.5%",
    "12.6%", "13.8%", "15.0%", "16.2%", "17.4%", "18.6%", "19.8%", "21.0%",
]
# fmt: on


def extract_vaild_info(info):
    """提取有效信息"""
    keys = []
    values = []

    def check_in(txt, valid_list):
        if txt in valid_list:
            return txt
        else:
            for k in valid_list:
                if k in txt:
                    return k
        return None

    for txt in info:
        if len(keys) >= 7 and len(values) >= 7:
            break

        if len(keys) < 7:
            key = check_in(txt, valid_keys)
            if key:
                keys.append(key)
                continue

        if len(values) < 7:
            txt = re.sub(r"[•·，,、,]", ".", txt)  # 替换为小数点
            txt = txt.replace("％", "%")
            if len(values) < 2:
                if "%" in txt:
                    match = re.search(r"(\d+(\.\d+)?)%", txt)
                    if match:
                        num = float(match.group(1))
                        formatted_num = f"{num:.1f}"
                        values.append(f"{formatted_num}%")
                else:
                    match = re.search(r"(\d+)", txt)
                    if match:
                        num = int(match.group(1))
                        if num <= 2280 and num >= 30:
                            values.append(str(num))
            else:
                key = check_in(txt, valid_values)
                if key:
                    values.append(key)
                    continue

    return keys, values


async def draw_char_with_ring(char_id) -> Image.Image:
    """绘制角色头像"""
    pic = await get_square_avatar(char_id)

    mask_pic = Image.open(TEXT_PATH / "avatar_mask.png")
    img = Image.new("RGBA", (150, 150))
    mask = mask_pic.resize((140, 140))
    resize_pic = crop_center_img(pic, 140, 140)
    img.paste(resize_pic, (5, 5), mask)

    return img


def fill_color(per):
    """填充颜色"""
    if per > 45:
        return (255, 0, 255, 250)  # 彩色（品红色，带透明度）
    elif 40 <= per <= 45:
        return (255, 50, 50, 250)  # 红色
    elif 30 <= per < 40:
        return (255, 215, 0, 250)  # 金色
    elif 10 <= per < 30:
        return (50, 205, 50, 250)  # 绿色
    else:
        return (255, 255, 255, 250)  # 白色（半透明）


async def draw_score(char_name, char_id, props, cost, calc_map):
    total_score, level = calc_phantom_score(char_name, props, cost, calc_map)
    level = level.upper()
    logger.debug(f"{char_name} [声骸分数]: {total_score} [声骸评分等级]: {level}")

    # 背景
    _, role_pile = await get_role_pile(char_id, True)
    bg_img = role_pile.resize((540, 680), Image.Resampling.LANCZOS)
    img = Image.new("RGBA", (540, 680), (30, 45, 65, 210))
    img = Image.alpha_composite(bg_img, img)

    # 头像部分
    avatar = await draw_char_with_ring(char_id)
    img.paste(avatar, (1, 0), avatar)

    ph_name_draw = ImageDraw.Draw(img)
    ph_name_draw.text((147, 73), f"{char_name}", "white", waves_font_36, "lm")
    ph_name_draw.text((147, 105), f"Cost {str(cost)}", "white", waves_font_24, "lm")

    # 总评分
    ph_score_img_draw = ImageDraw.Draw(img)
    ph_score_img_draw.rounded_rectangle([280, 60, 520, 110], radius=12, outline=(255, 255, 255, 100), width=1)
    ph_score_img_draw.text((320, 84), f"{total_score:.2f}   {level}", fill_color(total_score), waves_font_36, "lm")

    # 评分表
    sh_calc_map_draw = ImageDraw.Draw(img)
    sh_calc_map_draw.text((40, 165), f"[评分模版]：{calc_map['name']}", "white", waves_font_24, "lm")

    sh_temp = Image.new("RGBA", (404, 402), (25, 35, 55, 10))
    oset = 55
    for index, _prop in enumerate(props):
        char_model = get_char_model(char_id)
        char_attr = ""
        if char_model:
            char_attr = char_model.get_attribute_name()

        _, score = calc_phantom_entry(index, _prop, cost, calc_map, char_attr)
        logger.debug(f"{char_name} [属性]: {_prop.attributeName} {_prop.attributeValue} [评分]: {score}")

        prop_img = await get_attribute_prop(_prop.attributeName)
        prop_img = prop_img.resize((40, 40))
        sh_temp.alpha_composite(prop_img, (10, 15 + index * oset))

        sh_temp_draw = ImageDraw.Draw(sh_temp)
        name_color, num_color = get_valid_color(_prop.attributeName, _prop.attributeValue, calc_map)

        sh_temp_draw.text(
            (55, 35 + index * oset),
            f"{_prop.attributeName[:6]}",
            name_color,
            waves_font_24,
            "lm",
        )
        sh_temp_draw.text(
            (317, 35 + index * oset),
            f"{_prop.attributeValue}",
            num_color,
            waves_font_24,
            "rm",
        )

        sh_temp_draw.text(
            (395, 38 + index * oset),
            f"{score}分",
            fill_color((score / total_score) * 100),
            waves_font_18,
            "rm",
        )

    # 词条
    sh_temp_bg_draw = ImageDraw.Draw(img)
    sh_temp_bg_draw.rounded_rectangle([20, 205, 520, 322], radius=12, outline=(255, 255, 255, 100), width=1)
    sh_temp_bg_draw.rounded_rectangle([20, 324, 520, 610], radius=12, outline=(255, 255, 255, 100), width=1)
    img.alpha_composite(sh_temp, (68, 202))
    img = add_footer(img, 500)
    return await convert_img(img)


async def phantom_score_ocr(bot: Bot, ev: Event, char_name: str, cost: int):
    """声骸OCR查分"""
    at_sender = True if ev.group_id else False

    char_name = alias_to_char_name(char_name)
    char_id = char_name_to_char_id(char_name)
    if not char_id:
        return await bot.send(f"[鸣潮] 角色 {char_name} 无法找到, 可能暂未适配, 请先检查输入是否正确！\n", at_sender)

    if cost not in [1, 3, 4]:
        return await bot.send(f"[鸣潮][声骸查分] 不支持的cost:{cost}, 请重新输入！\n", at_sender)

    bool_i, images = await get_upload_img(ev)
    if not bool_i or not images:
        at_sender = True if ev.group_id else False
        await bot.send(
            "[鸣潮][声骸查分] 未获取到图片，请在30秒内发送声骸截图或图片链接\n(请保证图片清晰否则可能导致识别失败)\n",
            at_sender,
        )

        resp = await bot.receive_resp(timeout=30)
        if resp is not None:
            bool_i, images = await get_upload_img(ev)
        else:
            return await bot.send("[鸣潮] 等待超时，声骸查分已关闭\n", at_sender)

    if not bool_i or not images:
        return await bot.send("[鸣潮] 获取图片失败！声骸查分已关闭\n", at_sender)

    ocr_results = await ocrspace(images, bot, at_sender, language="chs", isTable=False)
    if isinstance(ocr_results, str):
        return await bot.send(ocr_results, at_sender)
    # ocr_results = [{'error': None, 'text':""},{'error': None, 'text': '矿岩机麋\n+25\nMAX\n×攻击\n×攻击\n• 暴击\n• 生命\n• 共鸣效率\n• 共鸣解放伤害加成\n• 攻击\n15100/15100\n•30.0%•\n•100\n10.5%\n360\n10•8%\n13.8%\n•9.4%'}]

    calc_temp = get_calc_map({}, char_name, char_id)
    msg = []
    for part in ocr_results:
        contexts = part["text"].split("\n")
        logger.debug(f"识别内容: {contexts}")
        keys, values = extract_vaild_info(contexts)
        logger.debug(f"提取词条: {keys}")
        logger.debug(f"提取值: {values}")

        if not keys or not values:
            msg.append("未识别到有效信息！\n")
            continue

        props = []
        if len(keys) != len(values):
            msg.append("识别到的词条和值数量不匹配！\n")
            continue

        for i in range(len(keys)):
            props.append(Props(attributeName=keys[i].replace("小", ""), attributeValue=values[i]))

        img = await draw_score(char_name, char_id, props, cost, calc_temp)
        msg.append(img)

    return await bot.send(msg, at_sender)
