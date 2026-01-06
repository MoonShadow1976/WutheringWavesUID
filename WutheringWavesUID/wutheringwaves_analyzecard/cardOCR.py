# 标准库
import re
from typing import Literal

# 项目内部模块
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
import numpy as np
from opencc import OpenCC
from PIL import Image

from ..wutheringwaves_analyzecard.userData import save_card_dict_to_json
from ..wutheringwaves_config import WutheringWavesConfig
from .detail_json import DETAIL
from .ocrspace import get_upload_img, ocrspace

cc = OpenCC("t2s")  # 繁体转简体

# 原始dc卡片参考分辨率，from example_card_2.png
REF_WIDTH = 1072
REF_HEIGHT = 602

# 裁切区域比例（左、上、右、下），数字来自src/example_card_2.png
# 技能树扫描顺序：普攻、共鸣技能、共鸣解放、变奏技能、共鸣回路(json_skillList顺序)
# 有可能出现空声骸，故放最后
crop_ratios = [
    (0 / REF_WIDTH, 0 / REF_HEIGHT, 420 / REF_WIDTH, 350 / REF_HEIGHT),  # 角色
    (890 / REF_WIDTH, 240 / REF_HEIGHT, 1020 / REF_WIDTH, 310 / REF_HEIGHT),  # 武器
    (583 / REF_WIDTH, 30 / REF_HEIGHT, 653 / REF_WIDTH, 130 / REF_HEIGHT),  # 普攻
    (456 / REF_WIDTH, 115 / REF_HEIGHT, 526 / REF_WIDTH, 215 / REF_HEIGHT),  # 共鸣技能
    (694 / REF_WIDTH, 115 / REF_HEIGHT, 764 / REF_WIDTH, 215 / REF_HEIGHT),  # 共鸣解放
    (501 / REF_WIDTH, 250 / REF_HEIGHT, 571 / REF_WIDTH, 350 / REF_HEIGHT),  # 变奏技能
    (650 / REF_WIDTH, 250 / REF_HEIGHT, 720 / REF_WIDTH, 350 / REF_HEIGHT),  # 共鸣回路
    (12 / REF_WIDTH, 360 / REF_HEIGHT, 216 / REF_WIDTH, 590 / REF_HEIGHT),  # 声骸1
    (221 / REF_WIDTH, 360 / REF_HEIGHT, 425 / REF_WIDTH, 590 / REF_HEIGHT),  # 声骸2
    (430 / REF_WIDTH, 360 / REF_HEIGHT, 634 / REF_WIDTH, 590 / REF_HEIGHT),  # 声骸3
    (639 / REF_WIDTH, 360 / REF_HEIGHT, 843 / REF_WIDTH, 590 / REF_HEIGHT),  # 声骸4
    (848 / REF_WIDTH, 360 / REF_HEIGHT, 1052 / REF_WIDTH, 590 / REF_HEIGHT),  # 声骸5 之间左右差209
]
# 共鸣链识别顺序（从右往左，从6到1）
chain_crop_ratios = [
    (321 / REF_WIDTH, 316 / REF_HEIGHT, 332 / REF_WIDTH, 327 / REF_HEIGHT),  # 6
    (276 / REF_WIDTH, 316 / REF_HEIGHT, 287 / REF_WIDTH, 327 / REF_HEIGHT),  # 5
    (231 / REF_WIDTH, 316 / REF_HEIGHT, 242 / REF_WIDTH, 327 / REF_HEIGHT),  # 4
    (186 / REF_WIDTH, 316 / REF_HEIGHT, 197 / REF_WIDTH, 327 / REF_HEIGHT),  # 3
    (141 / REF_WIDTH, 316 / REF_HEIGHT, 152 / REF_WIDTH, 327 / REF_HEIGHT),  # 2
    (100 / REF_WIDTH, 316 / REF_HEIGHT, 111 / REF_WIDTH, 327 / REF_HEIGHT),  # 1
]

# 原始角色裁切区域参考分辨率，from crop_ratios
CHAR_WIDTH = 420
CHAR_HEIGHT = 350
char_crop_ratios = [
    (37 / CHAR_WIDTH, 0 / CHAR_HEIGHT, 250 / CHAR_WIDTH, 45 / CHAR_HEIGHT),  # 上面角色名称与等级
    (0 / CHAR_WIDTH, 45 / CHAR_HEIGHT, 155 / CHAR_WIDTH, 80 / CHAR_HEIGHT),  # 下面用户昵称与id
]

# 原始声骸裁切区域参考分辨率，from crop_ratios
ECHO_WIDTH = 204
ECHO_HEIGHT = 230
echo_crop_ratios = [
    (110 / ECHO_WIDTH, 40 / ECHO_HEIGHT, 204 / ECHO_WIDTH, 60 / ECHO_HEIGHT),  # 右上角主词条(忽略声骸cost，暂不处理)
    (162 / ECHO_WIDTH, 60 / ECHO_HEIGHT, 204 / ECHO_WIDTH, 80 / ECHO_HEIGHT),  # 右上角主词条的值
    (24 / ECHO_WIDTH, 105 / ECHO_HEIGHT, 204 / ECHO_WIDTH, 230 / ECHO_HEIGHT),  # 下部6条副词条  zuo 左2
]

# 声骸图标和套装识别区域比例（左、上、右、下），数字来自src/example_card_2.png
echo_icon_crop_ratios = [
    (0 / ECHO_WIDTH, 2 / ECHO_HEIGHT, 107 / ECHO_WIDTH, 104 / ECHO_HEIGHT),  # 声骸
    # (139 136/ECHO_WIDTH, 10/ECHO_HEIGHT, 167 164/ECHO_WIDTH,  37/ECHO_HEIGHT), # 套装
    (137 / ECHO_WIDTH, 9 / ECHO_HEIGHT, 164 / ECHO_WIDTH, 37 / ECHO_HEIGHT),  # 套装
]


async def async_ocr(bot: Bot, ev: Event):
    """
    异步OCR识别函数
    """
    at_sender = True if ev.group_id else False

    bool_i, images = await get_upload_img(ev)
    if not bool_i or not images:
        return await bot.send("[鸣潮]获取dc卡片图失败！卡片分析已停止。\n", at_sender)
    # 获取dc卡片与共鸣链
    chain_num, chek_imgs, cropped_images = await cut_card_to_ocr(images[0])

    # 卡片词条OCR
    ocr_results = await ocrspace(cropped_images, bot, at_sender, need_all_pass=True)
    if isinstance(ocr_results, str):
        return await bot.send(ocr_results, at_sender)

    bool_d, final_result = await ocr_results_to_dict(chain_num, chek_imgs, ocr_results)
    if not bool_d:
        return await bot.send("[鸣潮]Please use chinese card！\n", at_sender)

    name, char_id = await which_char(bot, ev, final_result["角色信息"].get("角色名", ""))
    if char_id is None:
        logger.warning(f"[鸣潮][dc卡片识别] 角色[{name}]识别错误！")
        return await bot.send(f"[鸣潮]无法识别的角色名{name}，请确保图片清晰\n", at_sender)
    final_result["角色信息"]["角色名"] = name
    final_result["角色信息"]["角色ID"] = char_id

    await save_card_dict_to_json(bot, ev, final_result)


def cut_image(image: Image.Image, crop_ratios: list[tuple[float, float, float, float]]) -> list[Image.Image]:
    # 获取实际分辨率
    img_width, img_height = image.size
    # 裁切图片
    cropped_images = []
    for ratio in crop_ratios:
        # 根据相对比例计算实际裁切坐标
        left = ratio[0] * img_width
        top = ratio[1] * img_height
        right = ratio[2] * img_width
        bottom = ratio[3] * img_height

        # 四舍五入取整并确保不越界
        left = max(0, int(round(left)))
        top = max(0, int(round(top)))
        right = min(img_width, int(round(right)))
        bottom = min(img_height, int(round(bottom)))

        # 执行裁切
        cropped_image = image.crop((left, top, right, bottom))
        cropped_images.append(cropped_image)

    return cropped_images


def cut_image_need_data(
    image_need: Image.Image | list[Image.Image],
    data_crop_ratios: list[tuple[float, float, float, float]] = [],
    direction: Literal["down", "right"] = "down",
) -> Image.Image:
    """
    裁切声骸卡片拼接词条数据: 右上角主词条与余下6条副词条
    裁切角色卡片拼接用户数据: 上面角色数据，下面用户信息
    目的: 优化ocrspace 模型2识别

    参数:
    - image_need: 需要裁切的原始图像 或 需要拼接的子图列表
    - data_crop_ratios: 裁切比例列表，每个元素为 (left, top, right, bottom)
    - direction: 拼接方向，'down'（向下）或 'right'（向右），默认为 'down'

    返回:
    - image_only_data: 拼接后的图像
    """
    # 获取裁切后的子图列表
    cropped_images: list[Image.Image] = image_need if isinstance(image_need, list) else cut_image(image_need, data_crop_ratios)

    # 使用字典映射计算画布尺寸
    size_calc = {
        "down": lambda imgs: (
            max(img.width for img in imgs),
            sum(img.height for img in imgs),
        ),
        "right": lambda imgs: (
            sum(img.width for img in imgs),
            max(img.height for img in imgs),
        ),
    }

    canvas_size = size_calc[direction](cropped_images)

    # 使用字典映射计算偏移增量
    offset_increment = {
        "down": lambda img: (0, img.height),
        "right": lambda img: (img.width, 0),
    }

    # 创建新画布并逐个粘贴子图
    image_only_data = Image.new("RGB", canvas_size)
    x_offset, y_offset = 0, 0

    for img in cropped_images:
        image_only_data.paste(img, (x_offset, y_offset))
        dx, dy = offset_increment[direction](img)
        x_offset += dx
        y_offset += dy

    return image_only_data


def analyze_chain_num(image: Image.Image) -> int:
    cropped_chain_images = cut_image(image, chain_crop_ratios)

    avg_colors = []

    # 遍历切割后的图像区域
    for i, region in enumerate(cropped_chain_images):
        # 确保图像为RGB模式
        region = region.convert("RGB")
        region_array = np.array(region)

        # 计算平均颜色
        avg_r = int(np.mean(region_array[:, :, 0]))
        avg_g = int(np.mean(region_array[:, :, 1]))
        avg_b = int(np.mean(region_array[:, :, 2]))
        avg_colors.append((avg_r, avg_g, avg_b))

    def is_chain_color(color):
        """
        参考 rgb值 -- 3链
        (143, 129, 79)
        (144, 129, 80)
        (142, 128, 79)
        (203, 185, 127)
        (205, 189, 132)
        (207, 191, 135)
        360 与 530 的中值为 445
        """
        r, g, b = color
        return (r + g + b) > 445

    chain_num = 0
    chain_bool = False  # 共鸣链判断触发应连续
    for color in avg_colors:
        if not chain_bool and is_chain_color(color):
            chain_bool = True
            chain_num = 1
            continue
        if chain_bool and is_chain_color(color):
            chain_num += 1
            continue
        if chain_bool and not is_chain_color(color):
            logger.warning("[鸣潮]卡片分析 共鸣链识别出现断裂错误")
            return 0

    return chain_num


async def cut_card_to_ocr(image: Image.Image) -> tuple[int, list[dict], list[Image.Image]]:
    """
    裁切卡片：角色，技能树*5，声骸*5，武器
        （按比例适配任意分辨率，1920*1080识别效果优良）
    """

    # 分析角色共鸣链数据
    chain_num = analyze_chain_num(image)

    # 裁切卡片，分割识别范围
    cropped_images = cut_image(image, crop_ratios)

    # 进一步裁切角色图
    image_char = cropped_images[0]
    cropped_images[0] = cut_image_need_data(image_char, char_crop_ratios)

    # 进一步处理声骸图：裁切数值、图像匹配
    analyze_echoes_results = []
    for i in range(7, 12):
        image_echo = cropped_images[i]

        # 图像匹配部分
        if WutheringWavesConfig.get_config("CardImgCheck").data:
            cropped_icons = cut_image(image_echo, echo_icon_crop_ratios)
            from .img_check import batch_analyze_card_img

            results = await batch_analyze_card_img(cropped_icons, str(i - 6))
            analyze_echoes_results.append(results)

        # 裁切数值部分
        echo_values = cut_image(image_echo, echo_crop_ratios)
        echo_values_head = cut_image_need_data([echo_values[0], echo_values[1]], direction="right")
        cropped_images[i] = cut_image_need_data([echo_values_head, echo_values[2]])

        # from pathlib import Path # 保存裁切图片用于调试
        # SRC_PATH = Path(__file__).parent / "src"
        # cropped_images[i].save(f"{SRC_PATH}/_{i}.png")

    # 调用 images_ocrspace 函数并获取识别结果
    return chain_num, analyze_echoes_results, cropped_images


async def ocr_results_to_dict(chain_num: int, chek_imgs: list[dict], ocr_results: list[dict]) -> tuple[bool, dict[str, dict]]:
    """
    适配OCR.space输出结构的增强版结果解析
    输入结构: [{'text': '...', 'error': ...}, ...]
    """
    # 识别结果容器
    final_result = {"用户信息": {}, "角色信息": {}, "技能等级": [], "装备数据": {}, "匹配图标": {}, "武器信息": {}}

    # 保存角色共鸣链
    final_result["角色信息"]["共鸣链"] = chain_num

    # 保存声骸图标与套装匹配结果
    for result in chek_imgs:
        final_result["匹配图标"][f"{result['slot']}"] = {
            "echo_id": result["echo"],
            "sonata_name": result["echo_set"],
        }

    # 增强正则模式（适配多行文本处理）
    patterns = {
        "name": re.compile(
            r"^([A-Za-z\u4e00-\u9fa5\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7A3\u00C0-\u00FF]+)"
        ),  # 支持英文、中文、日文、韩文，以及西班牙文、德文和法文中的扩展拉丁字符，为后续逻辑判断用
        "level": re.compile(r"(?i)^(?:.*?V)?\s*?(\d+)$"),  # 兼容纯数字
        "skill_level": re.compile(r"(\d+)\s*[/ ]\s*\d*"),  # 兼容 L.10/10、LV.10/1、4 10、4/ 等格式
        "player_info": re.compile(r"玩家名(?:稱)?\s*[:：]?\s*(.*)$"),
        "uid_info": re.compile(r".[馬碼]\s*[:：]?\s*(\d+)"),
        "echo_cut": re.compile(r"([\u4e00-\u9fa5]+)\s*\D*([\d.]+%?)"),  # 分割各个词条与对应数值
        "echo_value": re.compile(
            r"([\u4e00-\u9fa5]+)\s*(?:\d+\s+)?\D*?([\d.]+%?)"
        ),  # 不支持英文词条(空格不好处理), 支持处理"暴擊傷害 器44%", "攻擊 ×18%", "熱熔傷害加成 0 3.75%"
        "weapon_info": re.compile(r"([\u4e00-\u9fa5]+)\s+LV\.(\d+)"),
    }

    # 处理角色信息（第一个识别结果）0
    if ocr_results:
        first_result = ocr_results[0]
        if first_result["text"] is not None:
            lines = first_result["text"].split("\t")  # 支持"◎\t洛可可\tLV.90\t"
            for line in lines:
                # 玩家名称
                player_match = patterns["player_info"].search(line)
                if player_match:
                    final_result["用户信息"]["玩家名称"] = player_match.group(1)
                    continue  # 避免玩家名称在前被识别为角色名

                # 文本预处理：删除非数字中英文的符号及多余空白
                line_clean = re.sub(
                    r"[^\u4e00-\u9fa5\u3040-\u309F\u30A0-\u30FF\uAC00-\uD7A3\u00C0-\u00FFA-Za-z0-9\s]", "", line
                )  # 先删除特殊符号, 匹配“漂泊者·湮灭”
                line_clean = re.sub(r"\s+", " ", line_clean).strip()  # 再合并多余空白

                # 角色名提取
                if not final_result["角色信息"].get("角色名"):
                    name_match = patterns["name"].search(line_clean)
                    if name_match:
                        name = name_match.group()
                        name = (
                            name.replace("吟槑", "吟霖").replace("鑒几", "鉴心").replace("千唉", "千咲").replace("千眹", "千咲")
                        )
                        if not re.match(r"^[\u4e00-\u9fa5]+$", name):
                            logger.warning(f" [鸣潮][dc卡片识别] 识别出非中文角色名:{name}，退出识别！")
                            return False, final_result
                        final_result["角色信息"]["角色名"] = cc.convert(name)

                # 等级提取
                line_num = re.sub(r"[oOQ○◌θ]", "0", line_clean)  # 处理0的错误识别
                line_num = re.sub(r"[^0-9\s]", "", line_num)
                level_match = patterns["level"].search(line_num)
                if level_match and not final_result["角色信息"].get("等级"):
                    final_result["角色信息"]["等级"] = min(int(level_match.group(1)), 90)  # 最大等级为90

                # UID提取
                uid_match = patterns["uid_info"].search(line_clean)
                if uid_match:
                    final_result["用户信息"]["UID"] = uid_match.group(1)

    # 处理武器信息（第二个结果）1
    if len(ocr_results) > 1 and ocr_results[1]["text"] is not None:
        text = ocr_results[1]["text"]
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 武器名称（取第一行有效文本）
        for line in lines:
            # 文本预处理：删除非数字中英文的符号及多余空白
            line_clean = re.sub(r"[oOQ○◌θ]", "0", line)  # 处理0的错误识别
            line_clean = re.sub(r"[^0-9\u4e00-\u9fa5\s]", "", line_clean)  # 先删除非数字中英文的符号, 匹配“源能臂铠·测肆”
            line_clean = re.sub(r"\s+", " ", line_clean).strip()  # 再合并多余空白
            if patterns["name"].search(line_clean):
                line_clean = line_clean.replace("幽冥的忘爱章", "幽冥的忘忧章")
                line_clean = re.sub(r".*古洑流$", "千古洑流", line_clean)
                final_result["武器信息"]["武器名"] = cc.convert(line_clean)
                continue

            level_match = patterns["level"].search(line_clean)
            if level_match:
                final_result["武器信息"]["等级"] = int(level_match.group(1))
                continue

    # 处理技能等级（第3-7个结果）下标：2 3 4 5 6
    for idx in range(2, 7):
        if idx >= len(ocr_results) or ocr_results[idx]["text"] is None:
            final_result["技能等级"].append(1)
            continue

        text = ocr_results[idx]["text"]
        # 强化文本清洗
        text_clean = re.sub(r"[oOQ○◌θ]", "0", text)  # 处理0的错误识别
        text_clean = re.sub(r"[^0-9/]", " ", text_clean)  # 将非数字字符替换为空格
        match = patterns["skill_level"].search(text_clean)
        if match:
            level = int(match.group(1))
            level = level if level > 0 else 1  # 限制最小等级为1
            final_result["技能等级"].append(min(level, 10))  # 限制最大等级为10
        else:
            logger.warning(f"[鸣潮][dc卡片识别]无法识别的技能等级：{text}")
            final_result["技能等级"].append(1)

    # 处理声骸装备（第8-12个结果）下标：7 8 9 10 11
    for idx in range(7, 12):
        if idx >= len(ocr_results) or ocr_results[idx]["text"] is None:
            continue

        equipment = {"mainProps": [], "subProps": []}
        text = ocr_results[idx]["text"]

        # 文本预处理：去除多余的空白符
        text_clean = re.sub(r"\s+", " ", text).strip()  # 使用 \s+ 匹配所有空白符，并替换为单个空格
        text_clean = re.sub(
            r"[·，,、,]", ".", text_clean
        )  # 将·与逗号替换为小数点(中文全角逗号（简体和繁体）、英文半角逗号、日文逗号（全角顿号）、韩文逗号)
        text_clean = text_clean.replace("％", "%")

        # 找到所有词条的位置
        matches = list(patterns["echo_cut"].finditer(text_clean))
        cut_entries = []
        # 处理每个词条段, 避免提取不全
        for i in range(len(matches)):
            if i < len(matches) - 1:
                text_value = text_clean[matches[i].start() : matches[i + 1].start()]
            else:
                text_value = text_clean[matches[i].start() :]
            if text_value:
                cut_entries.append(text_value)

        # 提取属性对
        valid_entries = []
        for entry in cut_entries:
            match = patterns["echo_value"].search(entry)
            if match:
                attr, value = match.groups()

                # 属性清洗
                attr = attr.strip()
                # 自定义替换优先执行（在繁转简之前）
                if re.search(r"暴.(傷害)?", attr):
                    attr = re.sub(r"暴.(傷害)?", r"暴擊\1", attr)
                attr = attr.replace("箓擎傷害", "暴擊傷害").replace("箓擎", "暴擊")
                attr = re.sub(r"^攻.*$", "攻擊", attr)
                attr = re.sub(r".*效率$", "共鳴效率", attr)
                attr = re.sub(r"^重.傷害加成*$", "重擊傷害加成", attr)
                clean_attr = cc.convert(attr)  # 标准繁简转换
                # 验证属性名是否符合预期（至少两个中文字符，且不含数字）
                if len(clean_attr) >= 2 and not re.search(r"[0-9]", clean_attr):
                    valid_entries.append((clean_attr, value))

        # 分配主副属性
        if valid_entries:
            # 主词条逻辑（取前两个有效词条）
            for entry in valid_entries[:2]:
                equipment["mainProps"].append({"attributeName": entry[0], "attributeValue": entry[1], "iconUrl": ""})

            # 副词条逻辑（取接下来5个有效词条）
            for entry in valid_entries[2:7]:
                equipment["subProps"].append({"attributeName": entry[0], "attributeValue": entry[1]})

            final_result["装备数据"][f"{idx - 6}"] = equipment
        else:
            final_result["装备数据"][f"{idx - 6}"] = None

    logger.info(f" [鸣潮][dc卡片识别] 最终提取内容:\n{final_result}")
    return True, final_result


async def which_char(bot: Bot, ev: Event, char: str) -> tuple[None | str, None | str]:
    if not char.strip():  # 为空
        return None, None

    at_sender = True if ev.group_id else False
    # 角色信息
    candidates = []
    for char_id, info in DETAIL.items():
        normalized_name = info["name"].replace("·", "").replace(" ", "")
        if char in normalized_name:
            candidates.append((char_id, info))
    logger.debug(f"[鸣潮][dc卡片识别] 角色匹配结果：{candidates}")

    if len(candidates) == 0:  # 无匹配
        return char, None

    if len(candidates) == 1:  # 唯一匹配
        char_id, info = candidates[0]
        return info["name"], char_id

    # 为漂泊者？
    options = []
    flat_choices = []  # 存储 (角色名, id)
    for idx, (char_id, info) in enumerate(candidates, 1):
        sex = info.get("sex", "未配置")
        options.append(f"{idx:>2}: [{sex}] {info['name']}")
        flat_choices.append((info["name"], char_id))

    # 构建双列布局
    paired_options = []
    for i in range(0, len(options), 2):
        line = []
        if i < len(options):
            line.append(options[i])
        if i + 1 < len(options):
            line.append(options[i + 1].ljust(30))  # 控制列宽
        paired_options.append("    ".join(line))  # 两列间用4空格分隔

    prompt = f"[鸣潮] 检测到{char}的多个分支：\n" + "\n".join(paired_options) + f"\n请于30秒内输入序号选择（1-{len(candidates)}）"
    await bot.send(prompt, at_sender=at_sender)

    # 第四步：处理用户响应
    try:
        error_count = 0
        while error_count < 3:
            resp = await bot.receive_resp(timeout=30)

            if resp is not None and resp.content[0].data and resp.content[0].type == "text" and resp.content[0].data.isdigit():
                choice_idx = int(resp.content[0].data) - 1
                if 0 <= choice_idx < len(flat_choices):
                    return flat_choices[choice_idx]
            error_count += 1
            await bot.send(
                prompt + f"\n\n---!-第{error_count}次重试-!---\n输入无效序号，请重新输入范围[1-{len(candidates)}]的数字选择\n",
                at_sender=at_sender,
            )

        # 超过3次错误
        default_name, default_id = flat_choices[0] if flat_choices else (char, None)
        await bot.send(f"[鸣潮] 选择多次出错，已自动使用 {default_name}\n", at_sender=at_sender)
        return default_name, default_id
    except Exception:
        default_name, default_id = flat_choices[0] if flat_choices else (char, None)
        await bot.send(f"[鸣潮] 选择出错，已自动使用 {default_name}\n", at_sender=at_sender)
        return default_name, default_id
