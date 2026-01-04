# change from https://github.com/alone-art/ScoreQuery


from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
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
    WAVES_FREEZING,
    WAVES_MOONLIT,
    add_footer,
    get_attribute_prop,
)
from ..utils.name_convert import alias_to_char_name, char_name_to_char_id

valid_keys = [
    "小生命",
    "生命",
    "小攻击",
    "攻击",
    "小防御",
    "防御",
    "共鸣效率",
    "暴击伤害",
    "暴击",
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
    "320",
    "360",
    "390",
    "430",
    "470",
    "510",
    "540",
    "580",
    "30",
    "40",
    "50",
    "60",
    "70",
    "6%",
    "6.0%",
    "6.4%",
    "7.1%",
    "7.9%",
    "8.6%",
    "9.4%",
    "10.1%",
    "10.9%",
    "11.6%",
    "8.1%",
    "9%",
    "9.0%",
    "10%",
    "10.0%",
    "10.9%",
    "11.8%",
    "12.8%",
    "13.8%",
    "14.7%",
    "6.8%",
    "7.6%",
    "8.4%",
    "9.2%",
    "10%",
    "10.0%",
    "10.8%",
    "11.6%",
    "12.4%",
    "6.3%",
    "6.9%",
    "7.5%",
    "8.1%",
    "8.7%",
    "9.3%",
    "9.9%",
    "10.5%",
    "12.6%",
    "13.8%",
    "15%",
    "15.0%",
    "16.2%",
    "17.4%",
    "18.6%",
    "19.8%",
    "21%",
    "21.0%",
]


def extract_vaild_info(info):
    keys = []
    values = []
    for txt in info:
        if len(keys) >= 7 and len(values) >= 7:
            break

        if len(keys) < 7:
            if txt in valid_keys:
                keys.append(txt)
            else:
                for k in valid_keys:
                    if k in txt:
                        keys.append(k)
                        break
        if len(values) < 7:
            if len(values) < 2:
                if "%" in txt:
                    values.append(txt)
                else:
                    try:
                        v = int(txt)
                        if v <= 2280 and v >= 30:
                            values.append(txt)
                    except ValueError:
                        pass
            elif txt in valid_values:
                values.append(txt)

    return keys, values


async def draw_ph(char_name, props, cost, calc_map):
    char_id = char_name_to_char_id(char_name)
    _score, _level = calc_phantom_score(char_name, props, cost, calc_map)
    _level = _level.upper()
    logger.info(f"{char_name} [声骸分数]: {_score} [声骸评分等级]: {_level}")

    img = Image.new("RGBA", (540, 680), (30, 45, 65, 0))

    sh_temp_bg_draw = ImageDraw.Draw(img)
    sh_temp_bg_draw.rounded_rectangle([20, 25, 520, 132], radius=12, fill=(25, 35, 55, 10))

    rect_width = (len(str(_score)) + len(str(_level)) + 3) * 18 + 20
    ph_score_img = Image.new("RGBA", (rect_width, 36), (255, 255, 255, 0))
    ph_score_img_draw = ImageDraw.Draw(ph_score_img)
    ph_score_img_draw.rounded_rectangle(
        [0, 0, ph_score_img.size[0], ph_score_img.size[1]], radius=8, fill=(186, 55, 42, int(0.8 * 255))
    )
    ph_score_img_draw.text((rect_width / 2, 18), f"{_score}分 {_level}", "white", waves_font_36, "mm")
    img.alpha_composite(ph_score_img, (280, 70))

    ph_name_draw = ImageDraw.Draw(img)
    ph_name_draw.text((78, 73), f"{char_name} ", "white", waves_font_36, "lm")
    ph_name_draw.text((78, 105), f"Cost {str(cost)}", "white", waves_font_18, "lm")

    sh_temp = Image.new("RGBA", (404, 402), (25, 35, 55, 10))
    oset = 55
    for index, _prop in enumerate(props):
        char_model = get_char_model(char_id)
        char_attr = ""
        if char_model:
            char_attr = char_model.get_attribute_name()

        _score, final_score = calc_phantom_entry(index, _prop, cost, calc_map, char_attr)
        logger.info(f"{char_name} [属性]: {_prop.attributeName} {_prop.attributeValue} [评分]: {final_score}")

        prop_img = await get_attribute_prop(_prop.attributeName)
        prop_img = prop_img.resize((40, 40))
        sh_temp.alpha_composite(prop_img, (15, 15 + index * oset))

        sh_temp_draw = ImageDraw.Draw(sh_temp)
        name_color = "white"
        num_color = "white"
        if index > 1:
            name_color, num_color = get_valid_color(_prop.attributeName, _prop.attributeValue, calc_map)

        sh_temp_draw.text(
            (60, 35 + index * oset),
            f"{_prop.attributeName[:6]}",
            name_color,
            waves_font_24,
            "lm",
        )
        sh_temp_draw.text(
            (318, 35 + index * oset),
            f"{_prop.attributeValue}",
            num_color,
            waves_font_24,
            "rm",
        )

        score_color = WAVES_MOONLIT
        if final_score > 0:
            score_color = WAVES_FREEZING
        sh_temp_draw.text(
            (388, 38 + index * oset),
            f"{final_score}分",
            score_color,
            waves_font_18,
            "rm",
        )

    sh_temp_bg_draw = ImageDraw.Draw(img)
    sh_temp_bg_draw.rounded_rectangle([20, 146, 520, 580], radius=12, fill=(25, 35, 55, 10))
    img.alpha_composite(sh_temp, (68, 162))
    img = add_footer(img, 600)
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

    # bool_i, images = await get_upload_img(ev)
    # if not bool_i or not images:
    #     at_sender = True if ev.group_id else False
    #     await bot.send(
    #         "[鸣潮][声骸查分] 未获取到图片，请在30秒内发送声骸截图或图片链接\n(请保证图片清晰否则可能导致识别失败)\n",
    #         at_sender,
    #     )

    #     resp = await bot.receive_resp(timeout=30)
    #     if resp is not None:
    #         bool_i, images = await get_upload_img(ev)
    #     else:
    #         return await bot.send("[鸣潮] 等待超时，声骸查分已关闭\n", at_sender)

    # if not bool_i or not images:
    #     return await bot.send("[鸣潮] 获取图片失败！声骸查分已关闭\n", at_sender)

    calc_temp = get_calc_map({}, char_name, -1)

    # ocr_results = await ocrspace(images, bot, at_sender, language="chs", isTable=False)
    # logger.info(f"识别内容: {ocr_results}")
    # if isinstance(ocr_results, str):
    #     return await bot.send(ocr_results, at_sender)
    ocr_results = [
        {"error": None, "text": ""},
        {
            "error": None,
            "text": "矿岩机麋\n+25\nMAX\n×攻击\n×攻击\n• 暴击\n• 生命\n• 共鸣效率\n• 暴击伤害\n• 攻击\n15100/15100\n30.0%\n100\n8.7%\n360\n10.8%\n13.8%\n9.4%",
        },
    ]

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

        img = await draw_ph(char_name, props, cost, calc_temp)
        msg.append(img)

    return await bot.send(msg, at_sender)
