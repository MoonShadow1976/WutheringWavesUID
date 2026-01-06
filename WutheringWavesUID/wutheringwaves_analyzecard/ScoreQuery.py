# change from https://github.com/alone-art/ScoreQuery

import io
from pathlib import Path
import re
from opencc import OpenCC
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw

from ..utils.api.model import Props
from ..utils.ascension.char import get_char_model
from ..utils.calculate import (
    calc_phantom_entry,
    calc_phantom_score,
    get_calc_map,
    get_valid_color,
)
from ..utils.fonts.waves_fonts import (
    waves_font_18,
    waves_font_20,
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

cc = OpenCC("t2s")  # 繁体转简体

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


def extract_vaild_info(info: list[str]) -> tuple[list, list]:
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
            txt = cc.convert(txt)
            key = check_in(txt, valid_keys)
            if not key:  # 适配ww面板图
                key = check_in(f"{txt}加成", valid_keys)
            if key:
                keys.append(key)
                continue

        if len(values) < 7:
            txt = re.sub(r"[:：•·，,、,]", ".", txt)  # 替换为小数点
            txt = txt.replace("％", "%")
            if len(values) < 1:
                if "%" in txt and re.match(r"^\d+(?:\.\d+)?%$", txt):
                    values.append(txt)
            elif len(values) == 1:
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


async def draw_char_with_ring(char_id: str) -> Image.Image:
    """绘制角色头像"""
    pic = await get_square_avatar(char_id)

    mask_pic = Image.open(TEXT_PATH / "avatar_mask.png")
    img = Image.new("RGBA", (150, 150))
    mask = mask_pic.resize((140, 140))
    resize_pic = crop_center_img(pic, 140, 140)
    img.paste(resize_pic, (5, 5), mask)

    return img


def fill_color(per: float) -> tuple[int, int, int, int]:
    """填充颜色"""
    if per > 45:
        return (123, 42, 38, 250)  # 深红色
    elif 40 <= per <= 45:
        return (255, 50, 50, 250)  # 红色
    elif 30 <= per < 40:
        return (255, 215, 0, 250)  # 金色
    elif 10 <= per < 30:
        return (50, 205, 50, 250)  # 绿色
    else:
        return (255, 255, 255, 250)  # 白色（半透明）


async def draw_score(char_name: str, char_id: str, props: list[Props], cost: int, calc_map: dict) -> bytes:
    total_score, level = calc_phantom_score(char_name, props, cost, calc_map)
    level = level.upper()
    logger.debug(f"{char_name} [声骸分数]: {total_score} [声骸评分等级]: {level}")

    # 背景
    _, role_pile = await get_role_pile(char_id, True)
    bg_img = role_pile.resize((540, 680))
    img = Image.new("RGBA", (540, 680), (30, 45, 65, 210))
    img = Image.alpha_composite(bg_img, img)

    # 头像部分
    avatar = await draw_char_with_ring(char_id)
    img.paste(avatar, (1, 0), avatar)

    ph_name_draw = ImageDraw.Draw(img)
    ph_name_draw.text((147, 73), f"{char_name}", "white", waves_font_24, "lm")
    ph_name_draw.text((147, 105), f"Cost {str(cost)}", "white", waves_font_18, "lm")

    # 总评分
    ph_score_img_draw = ImageDraw.Draw(img)
    ph_score_img_draw.text((315, 84), f"{total_score:.2f}   {level}", fill_color(total_score), waves_font_36, "lm")

    # 评分表
    sh_calc_map_draw = ImageDraw.Draw(img)
    sh_calc_map_draw.text((40, 165), f"[评分模版]：{calc_map['name']}", "white", waves_font_24, "lm")

    sh_temp = Image.new("RGBA", (404, 402), (25, 35, 55, 0))
    for index, _prop in enumerate(props):
        char_model = get_char_model(char_id)
        char_attr = ""
        if char_model:
            char_attr = char_model.get_attribute_name()

        _, score = calc_phantom_entry(index, _prop, cost, calc_map, char_attr)
        logger.debug(f"{char_name} [属性]: {_prop.attributeName} {_prop.attributeValue} [评分]: {score}")

        font = waves_font_20 if index == 1 else waves_font_24
        lset = 10 if index > 1 else 0
        oset = 45 if index > 1 else 50

        prop_img = await get_attribute_prop(_prop.attributeName)
        prop_img = prop_img.resize((40, 40))
        sh_temp.alpha_composite(prop_img, (10, 15 + index * oset + lset))

        sh_temp_draw = ImageDraw.Draw(sh_temp)
        name_color, num_color = get_valid_color(_prop.attributeName, _prop.attributeValue, calc_map)

        sh_temp_draw.text(
            (55, 35 + index * oset + lset),
            f"{_prop.attributeName[:6]}",
            name_color,
            font,
            "lm",
        )
        sh_temp_draw.text(
            (317, 35 + index * oset + lset),
            f"{_prop.attributeValue}",
            num_color,
            font,
            "rm",
        )

        sh_temp_draw.text(
            (395, 38 + index * oset + lset),
            f"{score}分",
            fill_color((score / total_score) * 100),
            waves_font_18,
            "rm",
        )

    # 词条
    sh_temp_bg_draw = ImageDraw.Draw(img)
    # sh_temp_bg_draw.rounded_rectangle([20, 205, 520, 322], radius=12, outline=(255, 255, 255, 100), width=1)
    # sh_temp_bg_draw.rounded_rectangle([20, 324, 520, 610], radius=12, outline=(255, 255, 255, 100), width=1)
    img.alpha_composite(sh_temp, (68, 202))
    img = add_footer(img, 500)
    img = img.resize((2160, 2720))
    return await convert_img(img)


def compress_image(images: list[Image.Image], max_size_kb: int) -> list[Image.Image]:
    max_size = max_size_kb * 1024
    result = []

    for img in images:
        img = img.convert("RGB")
        count = 0
        while True:
            buffer = io.BytesIO()
            img.save(buffer, "JPEG", quality=85, optimize=True)
            logger.debug(f"图片大小：{buffer.tell() / 1024:.2f}KB")
            count += 1

            if buffer.tell() <= max_size:
                break

            width, height = img.size
            scale = (max_size / buffer.tell()) ** 0.5
            new_width = max(300, int(width * scale))
            new_height = max(300, int(height * scale))

            # 如果尺寸已经是最小值，退出循环避免无限循环
            if new_width == width and new_height == height:
                logger.warning("压缩后的尺寸已经是最小值，无法继续压缩")
                break

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        logger.info(f"该图压缩了 {count}次, 最终大小：{buffer.tell() / 1024:.2f}KB")
        buffer.seek(0)
        result.append(Image.open(buffer))

    return result


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
            bool_i, images = await get_upload_img(resp)
        else:
            return await bot.send("[鸣潮] 等待超时，声骸查分已关闭\n", at_sender)

    if not bool_i or not images:
        return await bot.send("[鸣潮] 获取图片失败！声骸查分已关闭\n", at_sender)

    # 压缩image到90KB以内
    images = compress_image(images, 90)

    ocr_results = await ocrspace(images, bot, at_sender, language="chs", isTable=False)
    if isinstance(ocr_results, str):
        return await bot.send(ocr_results, at_sender)
    # ocr_results = [{'error': None, 'text':""},{'error': None, 'text': '◎\n暗鬃狼\nLv.25\n45.93分\n湮灭伤害加成\n攻击\n暴击伤害\n攻击\n该重击伤害加成\n众 共鸣技能伤害\n•暴击\n30.0%\n100\n21.0%\n11.6%\n9.4%\n10.9%\n10.5%'},{'error': None, 'text': 'COST\n11/12\n全部\n3\n合鸣筛选/全部\n+25\n+25\n+25\n+25\n未装备优先\n＜声骸推荐\n简述\n共鸣回•芙露德莉斯\n［COST 4\n+25\n器暴击伤害\n×攻击\n•普攻伤害加成\n暴击\n•牛命\n44.0%\n150\n10.9%\n9.9%\n6.4%\n390\n• 暴击伤害\n21.0%\n声骸技能\nC 使用声骸技能，召唤【破空幻刃】，\n攻击目标，造成八段27.36%和一段\n136.80%的气动伤害。\n在首位装配该声骸技能时，自身气动\n伤害加成提升10.00%，当装配角色\n为漂泊者•气动或卡提希娅时，自身\n气动伤害加成额外提升10.00%。\n卡提希娅装配中\n卸下\n培养\n特征码：117874920'}]

    calc_temp = get_calc_map({}, char_name, char_id)
    msg = []
    for part in ocr_results:
        if not part["text"]:
            msg.append("未识别到有效信息！请确保图片内容清晰规范！\n")
            continue

        contexts = part["text"].split("\n")
        logger.debug(f"识别内容: {contexts}")
        keys, values = extract_vaild_info(contexts)
        logger.info(f"提取词条: {keys}")
        logger.info(f"提取值: {values}")

        if not keys or not values:
            msg.append("未识别到有效信息！请确保图片内容清晰规范！\n")
            continue

        props = []
        if len(keys) != len(values):
            msg.append("识别到的词条和值数量不匹配！请确保图片内容清晰规范！\n")
            continue

        for i in range(len(keys)):
            props.append(Props(attributeName=keys[i].replace("小", ""), attributeValue=values[i]))

        try:
            img = await draw_score(char_name, char_id, props, cost, calc_temp)
        except Exception as e:
            logger.warning(f"程序错误：{e}")
            msg.append("词条错误！请确保图片内容清晰规范！\n")
            continue

        msg.append(img)

    if len(msg) == 1:
        return await bot.send(msg[0])
    return await bot.send(msg, at_sender)


# if __name__ == "__main__":
#     ocr_results =  [{'error': None, 'text': '亥强化\n锯袭铁影\n+25\nMAX\n*衍射伤害加成\n×攻击\n• 攻击\n• 暴击伤害\n• 共鸣解放伤害加成\n•暴击\n•共鸣效率\n*15100/15100\n30.0%\n100\n6.4%\n12.6%\n16.1%\n8.1%\n8.4%\n不限\n强化消耗材料（0/50）\n阶段放入'}]
#     for part in ocr_results:
#         contexts = part["text"].split("\n")
#         keys, values = extract_vaild_info(contexts)
#         print(f"提取词条: {keys}")
#         print(f"提取值: {values}")
