# change from https://github.com/alone-art/ScoreQuery

import copy
import difflib
import io
from pathlib import Path
import re
import time

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from opencc import OpenCC
from PIL import Image, ImageDraw

from ..utils.api.model import EquipPhantom, FetterDetail, PhantomProp, Props, RoleDetailData
from ..utils.ascension.char import get_char_model
from ..utils.at_help import ruser_id
from ..utils.cache import TimedCache
from ..utils.calc import WuWaCalc
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
from ..utils.name_convert import alias_to_char_name, char_name_to_char_id, phantom_id_to_phantom_name
from .char_fetterDetail import echo_data_to_cost, get_fetterDetail_from_char
from .ocrspace import get_upload_img, ocrspace
from .Phantom_check import PhantomValidator

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

WAIT_TIME = 120  # 等待时间 2分钟
timed_cache = TimedCache(timeout=WAIT_TIME, maxsize=10000)


def can_score_query_card(user_id: str) -> int:
    """检查是否可以分析卡片"""
    key = str(user_id)
    if timed_cache:
        now = int(time.time())
        time_stamp = timed_cache.get(key)
        if time_stamp and time_stamp > now:
            return time_stamp - now
    return 0


def set_cache_score_query_card(user_id: str, is_running: bool):
    """设置时限缓存"""
    key = str(user_id)
    if timed_cache:
        wait_time = WAIT_TIME if is_running else 0
        timed_cache.set(key, int(time.time()) + wait_time)


def extract_valid_info(info: list[str]) -> list[tuple[list, list, int]]:
    """提取有效信息"""
    result = []

    cost = None
    keys = []
    values = []

    for txt in info:
        txt = txt.strip()
        if not cost:
            cost_match = re.search(r"COST\s*(\d+)", txt, re.IGNORECASE)
            if cost_match:
                cost = int(cost_match.group(1))
                continue

        if len(keys) < 7:
            txt = cc.convert(txt)
            key = check_in(txt, valid_keys)
            if not key:  # 适配ww面板图
                key = check_in(f"{txt}加成", valid_keys)
            if key:
                keys.append(key)
                continue

        if len(values) < 7:
            txt = clean_ocr_num(txt)  # 清洗文本
            if len(values) < 1:  # 刚需主词条
                percent_match = re.search(r"(\d+(?:\.\d+)?%)", txt)
                if percent_match:
                    values.append(percent_match.group(1))
                    continue
            elif len(values) == 1:
                match = re.search(r"(\d+)", txt)
                if match:
                    num = int(match.group(1))
                    if num <= 2280 and num >= 30:
                        values.append(str(num))
                        continue
            else:
                key = check_in(txt, valid_values)
                if key:
                    values.append(key)
                    continue

        if len(keys) >= 7 and len(values) >= 7:
            result.append((keys[0:7], values[0:7], cost))
            keys = []
            values = []
            cost = None

    # 循环结束后，处理可能剩余的不完整声骸
    if keys and values and len(keys) == len(values):
        result.append((keys, values, cost))
    elif keys or values:
        # 数量不匹配，说明识别可能有误，记录日志但不添加
        logger.warning(f"丢弃不完整声骸: keys={keys}, values={values}, cost={cost}")

    return result


def check_in(txt, valid_list):
    if txt in valid_list:
        return txt
    for k in valid_list:
        if k in txt:
            return k

    close_matches = difflib.get_close_matches(txt, valid_list, n=1, cutoff=0.7)
    if close_matches:
        return close_matches[0]

    return None


def clean_ocr_num(txt: str) -> str:
    # 1. 全角转半角（数字、字母、符号）
    txt = re.sub(r"[０-９]", lambda x: chr(ord(x.group(0)) - 0xFEE0), txt)  # 全角数字
    txt = re.sub(r"[Ａ-Ｚａ-ｚ]", lambda x: chr(ord(x.group(0)) - 0xFEE0), txt)  # 全角字母
    txt = re.sub(
        r"[！＂＃＄％＆＇（）＊＋，．／：；＜＝＞？＠［＼］＾＿｀｛｜｝～－]", lambda x: chr(ord(x.group(0)) - 0xFEE0), txt
    )  # 全角标点
    txt = txt.replace("\u3000", " ")  # 全角空格

    # 2. 移除不可见字符
    txt = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]", "", txt)

    # 3. 统一各种形似小数点的符号（此时已半角化，正则可以简化）
    txt = re.sub(r"[•·‥…∶,`：';*_，、；。]", ".", txt)

    # 4. 合并连续小数点
    txt = re.sub(r"\.{2,}", ".", txt)

    # 5. 百分号归一化（此时全角％已在上文转为半角%，此步可保留以防遗漏）
    txt = re.sub(r"[％﹪٪]", "%", txt)

    return txt.strip()


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


async def _build_calc_ctx(role_detail: RoleDetailData) -> dict:
    """用本地角色数据构造 calc_temp 的条件上下文（chain / ph），供条件权重文件匹配。

    chain 取自本地角色的共鸣链，ph 取自主力声骸套装名。
    本地角色没有声骸数据时返回空 dict，get_calc_map 会回退到默认 calc.json。
    """
    if not (role_detail.phantomData and role_detail.phantomData.equipPhantomList):
        return {}

    calc: WuWaCalc = WuWaCalc(role_detail)
    calc.phantom_pre = calc.prepare_phantom()
    return calc.enhance_summation_phantom_value(calc.phantom_pre)


async def phantom_score_ocr(bot: Bot, ev: Event, char_name: str, cost: int):
    """声骸OCR查分"""
    at_sender = True if ev.group_id else False

    time_stamp = can_score_query_card(ev.user_id)
    if time_stamp > 0:
        return await bot.send(f"[鸣潮]声骸评分进行中，请等待评分完成或{time_stamp}秒后再进行评分！\n", at_sender)

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

    set_cache_score_query_card(ev.user_id, True)  # 设置时限
    ocr_results = await ocrspace(images, bot, at_sender, language="chs", isTable=False)
    set_cache_score_query_card(ev.user_id, False)  # 清除时限
    if isinstance(ocr_results, str):
        return await bot.send(ocr_results, at_sender)
    # ocr_results = [{'error': None, 'text': '异相•冰盈舞者\nCOST 1\n+25\n攻击\n◎ 生命\n•攻击\n• 暴击伤害\n•共鸣技能伤害加成\n• 暴击\n• 共鸣效率\n18.0%\n2280\n10.9%\n17.4%\n7.9%\n8.7%\n9.2%\n异相•冰盈舞者\nCOST 1\n+25\n攻击\n◎ 生命\n• 暴击\n• 暴击伤害\n• 共鸣解放伤害加成\n• 攻击\n•共鸣效率\n18.0%\n2280\n10.5%\n15.0%\n7.9%\n50\n10.0%'}]

    role_detail = await _load_local_role_detail(ev, char_id, char_name, ruser_id(ev))
    calc_ctx = await _build_calc_ctx(role_detail) if role_detail else {}
    calc_temp = get_calc_map(calc_ctx, char_name, char_id)
    msg = []
    for part in ocr_results:
        if not part["text"]:
            msg.append("未识别到有效信息！请确保图片内容清晰规范！\n")
            continue

        contexts = part["text"].split("\n")
        logger.debug(f"识别内容: {contexts}")
        results = extract_valid_info(contexts)
        if not results:
            msg.append("未识别到有效信息！请确保图片内容清晰规范！\n")
            continue

        for keys, values, ocr_cost in results:
            logger.info(f"[鸣潮][声骸查分] 提取结果: cost {ocr_cost}, 词条：{keys}, 数值：{values}")
            props = []
            if len(keys) != len(values):
                logger.warning(f"识别到的词条和值数量不匹配！keys: {keys}, values: {values}")
                msg.append("识别到的词条和值数量不匹配！请确保图片内容清晰规范！\n")
                continue

            for i in range(len(keys)):
                props.append(Props(attributeName=keys[i].replace("小", ""), attributeValue=values[i]))

            final_cost = ocr_cost if ocr_cost else cost

            # 声骸数据校验与修正（参考check_phantom_data）
            phantom_dict = {
                "cost": final_cost,
                "mainProps": [{"attributeName": p.attributeName, "attributeValue": p.attributeValue} for p in props[:2]],
                "subProps": [{"attributeName": p.attributeName, "attributeValue": p.attributeValue} for p in props[2:]],
            }
            validator = PhantomValidator([phantom_dict])
            is_valid, corrected_list = await validator.validate_phatom_list()
            if not is_valid or isinstance(corrected_list, str):
                msg.append(f"声骸数据异常：{corrected_list}！请确保图片内容清晰规范！\n")
                continue
            # 用修正后的值更新props
            corrected_ph = corrected_list[0]
            if corrected_ph:
                for j, pd in enumerate(corrected_ph.get("mainProps", [])):
                    if j < len(props) and pd:
                        props[j].attributeValue = pd["attributeValue"]
                for j, pd in enumerate(corrected_ph.get("subProps", [])):
                    idx = j + 2
                    if idx < len(props) and pd:
                        props[idx].attributeValue = pd["attributeValue"]

            try:
                img = await draw_score(char_name, char_id, props, final_cost, calc_temp)
            except Exception as e:
                logger.warning(f"程序错误：{e}")
                msg.append("词条错误！请确保图片内容清晰规范！\n")
                continue

            msg.append(img)

    if len(msg) == 1:
        return await bot.send(msg[0])
    if ev.bot_id in ["qq_official", "qqgroup"]:
        for img in msg:
            await bot.send(img, at_sender)
        return
    return await bot.send(msg, at_sender)


def build_equip_phantom(
    props: list[Props],
    cost: int,
    echo_id: int,
    name: str,
    fetter_template: dict,
    phantom_template: dict,
) -> EquipPhantom:
    """根据OCR识别到的词条列表、cost、声骸id与套装模板构造一个EquipPhantom。

    主词条与小词条放入mainProps（前2个），其余放入subProps，
    与cardOCR/echo_data_to_cost的输入结构保持一致。
    套装(fetterDetail)/声骸图标(phantomProp)沿用get_fetterDetail_from_char的模板。
    """
    main_props = props[:2] if len(props) >= 2 else props
    sub_props = props[len(main_props) :]
    return EquipPhantom(
        phantomProp=PhantomProp(
            phantomPropId=phantom_template.get("phantomPropId", 0),
            name=name,
            phantomId=echo_id,
            quality=phantom_template.get("quality", 5),
            cost=cost,
            iconUrl=phantom_template.get("iconUrl", ""),
            skillDescription=phantom_template.get("skillDescription"),
        ),
        cost=cost,
        quality=phantom_template.get("quality", 5),
        level=phantom_template.get("level", 25),
        fetterDetail=FetterDetail(
            groupId=fetter_template.get("groupId", 0),
            name=fetter_template.get("name", ""),
            iconUrl=fetter_template.get("iconUrl") or None,
            num=fetter_template.get("num", 0),
            firstDescription=fetter_template.get("firstDescription") or None,
            secondDescription=fetter_template.get("secondDescription") or None,
        ),
        mainProps=main_props,
        subProps=sub_props,
    )


def parse_extra_for_phantom_mapping(extra: str) -> tuple[dict[int, list[int]], str]:
    """从用户输入 extra 中解析「换声骸 X到Y [...]」位置映射。

    只有以「声骸」开头、且紧跟的正文中包含至少一个「数字到数字」模式
    的片段才视作 OCR 槽位映射指令（会被剥离并解析）；
    其他形似「换声骸主词条 c3 攻击」等没有位置映射的片段予以保留，
    仍通过 change_list_regex 传给 ChangeParser 处理。

    同一 OCR 序号可被映射到多个目标槽位（如「2到2 2到3」表示同一条OCR声骸
    同时放入槽 2、槽 3），此时 value 为长度 ≥ 1 的 list。

    返回:
        slot_mapping: ocr序号(0based) -> 目标槽位列表(0based，按出现顺序)
        cleaned_extra: 去掉位置映射型换声骸片段、去链接后
            可用于构造 change_list_regex 的文本
    """
    slot_mapping: dict[int, list[int]] = {}
    if not extra:
        return slot_mapping, ""

    # 剔除链接
    extra = re.sub(r"https?://[^\s]+", "", extra)

    # 按"换"拆分处理每一段
    segments = extra.split("换")
    kept: list[str] = []
    for seg in segments:
        stripped = seg.strip()
        if stripped.startswith("声骸"):
            content = stripped[len("声骸") :].strip()
            pairs = re.findall(r"(\d+)\s*到\s*(\d+)", content)
            if pairs:
                # 这是位置映射型换声骸片段 → 解析映射，不保留入 change_list_regex
                for from_pos, to_pos in pairs:
                    ocr_idx = int(from_pos) - 1
                    slot_idx = int(to_pos) - 1
                    if 0 <= ocr_idx < 5 and 0 <= slot_idx < 5:
                        slot_mapping.setdefault(ocr_idx, []).append(slot_idx)
                continue
            # 否则是非位置型换声骸（如「声骸主词条 c3 攻击」）→ 保留
        kept.append(seg)

    cleaned_extra = "换".join(kept).strip()
    return slot_mapping, cleaned_extra


def build_change_list_regex(cleaned_extra: str) -> str:
    """构造传递给 draw_char_detail_img 的 change_list_regex。

    固定前缀「换声骸 声骸ocr直出面板 1到5」始终放在最前面（系统OCR指令，保留）。
    用户输入中的「换声骸 X到Y ...」等自定义换声骸片段已在 parse_extra_for_phantom_mapping
    中被剥离并转为 slot_mapping（不走 ChangeParser），所以 cleaned_extra 里不会再出现；
    其余非声骸类变更命令（换武器/换角色/换合鸣/换面板等）追加在固定前缀之后。
    """
    FIXED_PREFIX = "换声骸 声骸ocr直出面板 1到5"
    cleaned_extra = (cleaned_extra or "").lstrip("换").strip()
    if not cleaned_extra:
        return FIXED_PREFIX
    return f"{FIXED_PREFIX}换{cleaned_extra}"


async def phantom_score_ocr_to_char(bot: Bot, ev: Event, char_name: str, extra: str = ""):
    """声骸OCR查分 -> 构造角色面板。

    用户输入声骸截图，OCR提取词条后构造为角色数据并绘制角色面板：
    - 默认为「顺序填充」：OCR识别出的声骸按顺序 1→2→3→4→5 填入槽位；
    - 若用户输入「换声骸 X到Y [...]」，则改为「映射填充（合并模式）」：
      * 先尝试加载用户已有角色或极限面板角色的原始声骸列表；
      * 按映射将 OCR 第 X 个声骸放入槽位 Y，其余槽位保留原有声骸；
      * 若无法获取任何可用的基准声骸，则忽略映射指令，回退顺序填充。
    """
    at_sender = True if ev.group_id else False

    time_stamp = can_score_query_card(ev.user_id)
    if time_stamp > 0:
        return await bot.send(
            f"[鸣潮]声骸评分进行中，请等待评分完成或{time_stamp}秒后再进行评分！\n",
            at_sender,
        )

    char_name = alias_to_char_name(char_name)
    char_id = char_name_to_char_id(char_name)
    if not char_id:
        return await bot.send(
            f"[鸣潮] 角色 {char_name} 无法找到, 可能暂未适配, 请先检查输入是否正确！\n",
            at_sender,
        )

    # ---------- 1. 解析换声骸位置映射 ----------
    slot_mapping, cleaned_extra = parse_extra_for_phantom_mapping(extra)

    # ---------- 2. 收取图片 + OCR ----------
    bool_i, images = await get_upload_img(ev)
    if not bool_i or not images:
        await bot.send(
            "[鸣潮][角色评分] 未获取到图片，请在30秒内发送5张以内的声骸截图或图片链接\n(请保证图片清晰否则可能导致识别失败)\n",
            at_sender,
        )

        resp = await bot.receive_resp(timeout=30)
        if resp is not None:
            bool_i, images = await get_upload_img(resp)
        else:
            return await bot.send("[鸣潮] 等待超时，角色评分已关闭\n", at_sender)

    if not bool_i or not images:
        return await bot.send("[鸣潮] 获取图片失败！角色评分已关闭\n", at_sender)

    # 压缩image到90KB以内
    images = compress_image(images, 90)

    set_cache_score_query_card(ev.user_id, True)  # 设置时限
    ocr_results = await ocrspace(images, bot, at_sender, language="chs", isTable=False)
    set_cache_score_query_card(ev.user_id, False)  # 清除时限
    if isinstance(ocr_results, str):
        return await bot.send(ocr_results, at_sender)

    # ocr_results = [{
    #     "error": None,
    #     "text": "COST 4\n+25\n暴击伤害\n攻击\n• 暴击\n• 防御\n• 暴击伤害\n•生命\n• 攻击\n 44,0%66\nL 150\n8.7%\n• 60\n21.0%\n8.6%\n10.1%\n",
    # }]

    # ---------- 3. 收集 OCR 原始声骸（不超过 5 个）----------
    # 每个元素: (props, main_props_dicts)  ——  props 已去掉"小"前缀
    ECHO = await get_fetterDetail_from_char(char_id)
    ocr_raw_list: list[tuple[list[Props], list[dict]]] = []
    for part in ocr_results:
        if not part["text"]:
            continue
        contexts = part["text"].split("\n")
        logger.debug(f"[鸣潮][角色评分] 识别内容: {contexts}")
        results = extract_valid_info(contexts)
        if not results:
            continue

        for keys, values, ocr_cost in results:
            if len(ocr_raw_list) >= 5:
                break
            logger.info(f"[鸣潮][角色评分] 提取结果: cost {ocr_cost}, 词条：{keys}, 数值：{values}")
            if len(keys) != len(values):
                logger.warning(f"识别到的词条和值数量不匹配！keys: {keys}, values: {values}")
                continue

            props = [Props(attributeName=keys[i].replace("小", ""), attributeValue=values[i]) for i in range(len(keys))]
            if len(props) < 2:
                logger.warning(f"[鸣潮][角色评分] 识别词条不足2个，无法判定cost，跳过: {keys}")
                continue

            main_props_dicts = [
                {"attributeName": props[0].attributeName, "attributeValue": props[0].attributeValue},
                {"attributeName": props[1].attributeName, "attributeValue": props[1].attributeValue},
            ]
            ocr_raw_list.append((props, main_props_dicts))

    if not ocr_raw_list:
        return await bot.send(
            "[鸣潮][角色评分] 未识别到有效声骸信息！请确保图片内容清晰规范！\n",
            at_sender,
        )

    # ---------- 4. 决定构建模式：映射合并 / 顺序填充 ----------
    use_merge_mode = False
    base_phantom_list: list[EquipPhantom | None] = [None] * 5
    if slot_mapping:
        # 有用户映射指令：尝试加载已有角色声骸作为基准
        base_list = await _load_base_equiphantom_list(ev, char_id, char_name, ruser_id(ev))
        if base_list is not None and any(p is not None for p in base_list):
            # 基准有可用声骸 → 启用合并模式
            base_phantom_list = list(base_list)
            while len(base_phantom_list) < 5:
                base_phantom_list.append(None)
            use_merge_mode = True
        else:
            logger.info(
                f"[鸣潮][角色评分] 用户输入了换声骸映射{slot_mapping}，但无法获取已有角色的基准声骸列表 → 忽略映射，按顺序填充"
            )

    equip_phantom_list: list[EquipPhantom | None]
    if use_merge_mode:
        equip_phantom_list = await _build_merged_equip_phantom_list(
            char_id,
            ECHO,
            ocr_raw_list,
            slot_mapping,
            base_phantom_list,
        )
    else:
        equip_phantom_list = await _build_sequential_equip_phantom_list(
            char_id,
            ECHO,
            ocr_raw_list,
        )

    if not equip_phantom_list or all(p is None for p in equip_phantom_list):
        return await bot.send(
            "[鸣潮][角色评分] 未识别到有效声骸信息！请确保图片内容清晰规范！\n",
            at_sender,
        )

    # ---------- 5. 声骸数据校验与修正（PhantomValidator）----------
    phantom_dicts = []
    for ep in equip_phantom_list:
        if ep:
            d = ep.model_dump()
            phantom_dicts.append(d)
        else:
            phantom_dicts.append(None)

    validator = PhantomValidator(phantom_dicts)
    is_valid, corrected_list = await validator.validate_phatom_list()
    if not is_valid or isinstance(corrected_list, str):
        return await bot.send(
            f"[鸣潮][角色评分] 声骸数据异常：{corrected_list}！\n请调整异常声骸位置后或使用更高分辨率图片重新识别！\n",
            at_sender,
        )

    # 用修正后的值更新EquipPhantom的props
    for i, corrected in enumerate(corrected_list):
        if corrected and equip_phantom_list[i]:
            ep = equip_phantom_list[i]
            if ep and ep.mainProps and corrected.get("mainProps"):
                for j, pd in enumerate(corrected["mainProps"]):
                    if j < len(ep.mainProps) and pd:
                        ep.mainProps[j].attributeValue = pd["attributeValue"]
            if ep and ep.subProps and corrected.get("subProps"):
                for j, pd in enumerate(corrected["subProps"]):
                    if j < len(ep.subProps) and pd:
                        ep.subProps[j].attributeValue = pd["attributeValue"]

    # ---------- 6. 调用 draw_char_detail_img ----------
    # 延迟导入避免循环依赖
    from ..utils.database.models import WavesBind
    from ..wutheringwaves_charinfo.draw_char_card import draw_char_detail_img

    uid = await WavesBind.get_uid_by_game(ruser_id(ev), ev.bot_id)
    change_list_regex = build_change_list_regex(cleaned_extra)
    logger.debug(
        f"[鸣潮][角色评分] 角色: {char_name}, 合并模式: {use_merge_mode}, "
        f"映射: {slot_mapping}, change_list: {change_list_regex!r}"
    )
    if uid:
        im = await draw_char_detail_img(
            ev,
            uid,
            char_name,
            ruser_id(ev),
            change_list_regex=change_list_regex,
            override_equip_phantom_list=equip_phantom_list,
        )
    else:
        # 未绑定uid，使用默认账户构造（极限查询模式）
        im = await draw_char_detail_img(
            ev,
            "1",
            char_name,
            ruser_id(ev),
            is_limit_query=True,
            change_list_regex=change_list_regex,
            override_equip_phantom_list=equip_phantom_list,
        )

    if isinstance(im, str) or isinstance(im, bytes):
        return await bot.send(im, at_sender)


async def _load_local_role_detail(ev, char_id: str, char_name: str, user_id) -> RoleDetailData | None:
    """加载本地角色数据（或极限面板角色数据），失败时回退到构造的默认角色数据。"""
    # 延迟导入避免循环依赖
    from ..utils.database.models import WavesBind
    from ..wutheringwaves_charinfo.draw_char_card import (
        generate_online_role_detail,
        get_role_need,
    )

    uid = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    is_limit_query = not bool(uid)
    use_uid = uid if uid else "1"

    force_resource_id = char_id if is_limit_query else None

    _avatar, role_detail = await get_role_need(
        ev,
        char_id,
        "",  # ck
        use_uid,
        char_name,
        None,  # waves_id
        False,  # is_force_avatar
        force_resource_id,
        False,  # is_online_user
        is_limit_query,
    )
    if isinstance(role_detail, str) or not role_detail:
        role_detail = await generate_online_role_detail(char_id)
    return role_detail if isinstance(role_detail, RoleDetailData) else None


async def _load_base_equiphantom_list(
    ev,
    char_id: str,
    char_name: str,
    user_id,
) -> list[EquipPhantom | None] | None:
    """尝试加载已有角色（或极限面板角色）的声骸列表作为合并基准。

    返回:
        长度为5的列表（含 None）表示可用基准；
        None 表示没有任何可用基准（此时应忽略换声骸映射指令）。
    """
    role_detail = await _load_local_role_detail(ev, char_id, char_name, user_id)
    if not role_detail:
        return None

    equip_list: list[EquipPhantom | None] = [None] * 5
    if role_detail.phantomData and role_detail.phantomData.equipPhantomList:
        src = role_detail.phantomData.equipPhantomList
        for i in range(min(5, len(src))):
            equip_list[i] = src[i]
    return equip_list


async def _build_sequential_equip_phantom_list(
    char_id,
    ECHO: list[dict],
    ocr_raw_list: list[tuple[list[Props], list[dict]]],
) -> list[EquipPhantom | None]:
    """顺序填充：OCR第1个→槽1, OCR第2个→槽2 ……（最多5个）"""
    cost4_counter = 0
    equip_phantom_list: list[EquipPhantom | None] = []
    for slot in range(min(len(ocr_raw_list), 5)):
        props, main_props_dicts = ocr_raw_list[slot]
        echo_id, cost = await echo_data_to_cost(char_id, main_props_dicts, slot, cost4_counter)
        name = (phantom_id_to_phantom_name(str(echo_id)) if cost == 4 else "") or f"识别默认{cost}c"

        sonata_echo = copy.deepcopy(ECHO[slot]) if slot < len(ECHO) else {}
        fetter_template = sonata_echo.get("fetterDetail", {}) if sonata_echo else {}
        phantom_template = sonata_echo.get("phantomProp", {}) if sonata_echo else {}

        equip_phantom_list.append(build_equip_phantom(props, cost, echo_id, name, fetter_template, phantom_template))
        if cost == 4:
            cost4_counter += 1
    return equip_phantom_list


async def _build_merged_equip_phantom_list(
    char_id,
    ECHO: list[dict],
    ocr_raw_list: list[tuple[list[Props], list[dict]]],
    slot_mapping: dict[int, list[int]],
    base_phantom_list: list[EquipPhantom | None],
) -> list[EquipPhantom | None]:
    """合并填充：保留基准声骸，按映射替换指定槽位。

    同一条 OCR 声骸可被放入多个槽位（dict value 为 list[int]），
    每一个目标槽位都会独立用其槽位号调用 echo_data_to_cost 并生成
    一份独立的 EquipPhantom（这样 cost/套装模板/4cost id 都与对应槽位匹配）。
    ocr序号超出 OCR 列表范围的映射忽略；目标槽位越界忽略。
    cost4_counter 从基准中的 4cost 数量开始累计，每生成一个 4cost
    副本就递增。映射处理按目标槽位升序依次展开，保证 slot=0 时
    echo_data_to_cost 的 needId 分支优先命中。
    """
    merged: list[EquipPhantom | None] = list(base_phantom_list)
    while len(merged) < 5:
        merged.append(None)

    # 计算基准已有 4cost 数量，用于延续ID循环
    cost4_counter = sum(1 for p in merged if p is not None and getattr(p, "cost", 0) == 4)

    # 展开成 [(slot_idx, ocr_idx), ...]，按 slot_idx 升序处理
    flat_pairs: list[tuple[int, int]] = []
    for ocr_idx, slot_indices in slot_mapping.items():
        for slot_idx in slot_indices:
            flat_pairs.append((slot_idx, ocr_idx))
    flat_pairs.sort(key=lambda kv: kv[0])

    for slot_idx, ocr_idx in flat_pairs:
        if ocr_idx < 0 or ocr_idx >= len(ocr_raw_list):
            logger.debug(f"[鸣潮][角色评分] ocr序号{ocr_idx + 1}超出范围，跳过映射")
            continue
        if slot_idx < 0 or slot_idx >= 5:
            logger.debug(f"[鸣潮][角色评分] 目标槽位{slot_idx + 1}超出范围，跳过映射")
            continue
        props, main_props_dicts = ocr_raw_list[ocr_idx]
        echo_id, cost = await echo_data_to_cost(char_id, main_props_dicts, slot_idx, cost4_counter)
        name = (phantom_id_to_phantom_name(str(echo_id)) if cost == 4 else "") or f"识别默认{cost}c"

        sonata_echo = copy.deepcopy(ECHO[slot_idx]) if slot_idx < len(ECHO) else {}
        fetter_template = sonata_echo.get("fetterDetail", {}) if sonata_echo else {}
        phantom_template = sonata_echo.get("phantomProp", {}) if sonata_echo else {}

        merged[slot_idx] = build_equip_phantom(props, cost, echo_id, name, fetter_template, phantom_template)
        if cost == 4:
            cost4_counter += 1

    return merged


# if __name__ == "__main__":
#     ocr_results = [
#         {
#             "error": None,
#             "text": "《声骸推荐\n简述\n哀声鸷气动\nCOST 4\n+25\n暴然伤害\n×攻击中\n• 暴击\n• 防御\n• 暴击伤害\n•王命\n• 攻击\n666: 44,0%66\nL 150\n8.7%\n• 60\n21.0%\n8.6%\n10.1%\n声骸技能\n◎ 召唤梦魇•哀声鸷，对周围敌人造成\n衍射伤害，对受「光噪效应」影响的\n敌人造成更多伤害。在首位装配时提\n高自身的衍射伤害。\n合鸣效果\nY 此间永驻之光\n（2/2）\n衍射伤害提升\n赞妮装配中",
#         }
#     ]
#     for part in ocr_results:
#         contexts = part["text"].split("\n")
#         keys, values = extract_valid_info(contexts)
#         print(f"提取词条: {keys}")
#         print(f"提取值: {values}")
