from collections import defaultdict
import copy
from pathlib import Path
import textwrap

from gsuid_core.logger import logger
from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw

from ..utils.ascension.echo import echo_id_data, set_name_to_echo_ids
from ..utils.ascension.sonata import sonata_id_data
from ..utils.ascension.weapon import weapon_id_data
from ..utils.fonts.waves_fonts import waves_font_16, waves_font_18, waves_font_24, waves_font_36
from ..utils.image import (
    SPECIAL_GOLD,
    add_footer,
    get_attribute_effect,
    get_square_weapon,
    get_waves_bg,
)
from ..utils.name_convert import alias_to_sonata_name
from ..utils.resource.constant import get_short_name
from ..utils.resource.download_file import get_phantom_img
from ..wutheringwaves_config import PREFIX

TEXT_PATH = Path(__file__).parent.parent / "wutheringwaves_develop" / "texture2d"
star_1 = Image.open(TEXT_PATH / "star-1.png")
star_2 = Image.open(TEXT_PATH / "star-2.png")
star_3 = Image.open(TEXT_PATH / "star-3.png")
star_4 = Image.open(TEXT_PATH / "star-4.png")
star_5 = Image.open(TEXT_PATH / "star-5.png")
star_img_map = {
    1: star_1,
    2: star_2,
    3: star_3,
    4: star_4,
    5: star_5,
}


async def draw_weapon_list(weapon_type: str):
    # 确保数据已加载
    if not weapon_id_data:
        return "[鸣潮][武器列表]暂无数据"

    # 武器类型映射
    weapon_type_map = {
        1: "长刃",
        2: "迅刀",
        3: "佩枪",
        4: "臂铠",
        5: "音感仪",
    }

    # 创建反向映射（中文类型 → 数字类型）
    reverse_type_map = {v: k for k, v in weapon_type_map.items()}
    logger.debug(f"正在处理武器类型：{weapon_type}")
    logger.debug(f"正在处理武器列表：{reverse_type_map}")

    # 按武器类型分组收集武器数据
    weapon_groups = defaultdict(list)
    target_type = reverse_type_map.get(weapon_type)
    logger.debug(f"成功处理：{target_type}")

    for weapon_id, data in weapon_id_data.items():
        name = data.get("name", "未知武器")
        star_level = data.get("starLevel", 0)
        w_type = data.get("type", 0)  # 注意：避免与参数同名冲突
        effect_name = data.get("effectName", "")

        # 如果找到目标类型，只收集该类型武器
        if target_type is not None:
            if w_type == target_type:
                weapon_groups[w_type].append(
                    {"id": weapon_id, "name": name, "star_level": star_level, "effect_name": effect_name}
                )
        # 否则收集所有武器
        else:
            weapon_groups[w_type].append({"id": weapon_id, "name": name, "star_level": star_level, "effect_name": effect_name})

    # 按类型从小到大排序
    sorted_groups = sorted(weapon_groups.items(), key=lambda x: x[0])

    # 每行武器数量（单类型4列，全部类型9列）
    weapons_per_row = 9 if target_type is None else 4
    # 图标大小
    icon_size = 120
    # 水平间距
    horizontal_spacing = 150

    # 创建更宽的背景图（1800宽度）
    width = horizontal_spacing * (weapons_per_row - 1) + icon_size + 80
    img = get_waves_bg(width, 4000, "bg5")
    draw = ImageDraw.Draw(img)

    # 绘制标题
    title = "武器一览"
    draw.text((int(width / 2), 25), title, font=waves_font_36, fill=SPECIAL_GOLD, anchor="mt")
    draw.text(
        (int(width / 2), 63), f"使用【{PREFIX}'武器名'介绍】查询武器具体信息", font=waves_font_24, fill="#AAAAAA", anchor="mt"
    )

    # 当前绘制位置
    y_offset = 90

    # 添加组间分隔线
    draw.line((40, y_offset, width - 40, y_offset), fill=SPECIAL_GOLD, width=1)
    # 绘制武器效果名（灰色）y_offset += 20

    # 按武器类型遍历所有分组
    for weapon_type, weapons in sorted_groups:
        # 获取类型名称
        type_name = weapon_type_map.get(int(weapon_type), f"未知类型{weapon_type}")

        # 绘制类型标题
        draw.text((50, y_offset), type_name, font=waves_font_24, fill=SPECIAL_GOLD)
        y_offset += 40

        # 按星级降序排序（高星在前）
        weapons.sort(key=lambda x: (-x["star_level"], x["name"]))

        # 计算该组需要的行数
        rows = (len(weapons) + weapons_per_row - 1) // weapons_per_row

        # 计算图标和名称的高度
        name_height = 25
        effect_name_height = 20
        row_height = icon_size + name_height + effect_name_height + 30

        # 绘制武器组
        for row in range(rows):
            row_y = y_offset  # 当前行起始位置

            # 绘制该行所有武器
            for col in range(weapons_per_row):
                index = row * weapons_per_row + col
                if index >= len(weapons):
                    break

                weapon = weapons[index]

                # 计算位置（居中布局）
                x_pos = 40 + col * horizontal_spacing

                # 获取武器图标
                weapon_icon = await get_square_weapon(weapon["id"])
                weapon_icon = weapon_icon.resize((icon_size, icon_size))

                # 获取并调整武器背景框
                star_img = copy.deepcopy(star_img_map[weapon["star_level"]])
                star_img = star_img.resize((icon_size, icon_size))
                img.alpha_composite(weapon_icon, (x_pos, row_y))
                img.alpha_composite(star_img, (x_pos, row_y))

                # 绘制武器名称
                draw.text(
                    (x_pos + icon_size // 2, row_y + icon_size + 10),
                    weapon["name"],
                    font=waves_font_18,
                    fill="white",
                    anchor="mt",
                )

                # 绘制武器效果名（灰色）
                draw.text(
                    (x_pos + icon_size // 2, row_y + icon_size + 35),
                    weapon["effect_name"],
                    font=waves_font_16,
                    fill="#AAAAAA",  # 灰色
                    anchor="mt",
                )

            # 移动到下一行
            y_offset += row_height

        # 添加组间分隔线
        draw.line((40, y_offset, width - 40, y_offset), fill=SPECIAL_GOLD, width=1)
        y_offset += 20

    # 裁剪图片到实际高度
    img = img.crop((0, 0, width, y_offset + 50))
    img = add_footer(img, int(width / 2), 10)  # 页脚居中
    return await convert_img(img)


async def draw_sonata_list():
    # 确保数据已加载
    if not sonata_id_data:
        return "[鸣潮][套装列表]暂无数据"

    # 收集所有声骸套装数据
    sonata_groups = defaultdict(list)
    for data in sonata_id_data.values():
        name = data.get("name", "未知套装")
        set_list = data.get("set", {})
        # 按名称字数分组
        word_count = len(name)
        sonata_groups[word_count].append({"name": name, "set": set_list})

    # 按字数从小到大排序
    sorted_groups = sorted(sonata_groups.items(), key=lambda x: x[0])

    # 创建背景图（高度暂定，后面会调整）
    img = get_waves_bg(1440, 3000, "bg5")
    draw = ImageDraw.Draw(img)

    # 绘制标题
    title = "声骸套装一览"
    draw.text((700, 25), title, font=waves_font_36, fill=SPECIAL_GOLD, anchor="mt")
    draw.text((700, 63), f"使用【{PREFIX}'套装名'声骸列表】查看指定套装声骸", font=waves_font_24, fill="#AAAAAA", anchor="mt")

    # 当前绘制位置
    y_offset = 90
    col_width = 14  # 列宽调整为14个字符（四列布局）
    des_height = 25  # 套装效果描述高度

    # 列配置
    col_config = [
        {"x": 40, "icon_x": 40, "text_x": 100},  # 第1列
        {"x": 380, "icon_x": 380, "text_x": 440},  # 第2列
        {"x": 720, "icon_x": 720, "text_x": 780},  # 第3列
        {"x": 1060, "icon_x": 1060, "text_x": 1120},  # 第4列
    ]

    # 添加组间分隔线
    draw.line((40, y_offset, 1400, y_offset), fill=SPECIAL_GOLD, width=1)
    y_offset += 20

    # 按字数从小到大遍历所有分组
    for word_count, sonatas in sorted_groups:
        # 对组内套装按名称排序
        sonatas.sort(key=lambda x: x["name"])

        # 将组内套装分成四列展示
        for i in range(0, len(sonatas), 4):
            current_y = y_offset  # 记录当前行的起始Y位置
            max_height = 0  # 记录当前行最大高度

            # 遍历当前行的4个套装
            for col_idx in range(4):
                if i + col_idx >= len(sonatas):
                    break

                sonata = sonatas[i + col_idx]
                name_height = 30

                # 获取当前列的配置
                col_info = col_config[col_idx]

                # 获取套装图标
                fetter_icon = await get_attribute_effect(sonata["name"])
                fetter_icon = fetter_icon.resize((50, 50))
                img.paste(fetter_icon, (col_info["icon_x"], current_y), fetter_icon)

                # 绘制套装名称
                draw.text(
                    (col_info["text_x"], current_y),
                    sonata["name"],
                    font=waves_font_24,
                    fill=SPECIAL_GOLD,
                )

                # 绘制所有套装效果
                current_height = current_y + name_height
                for set_num, effect in sorted(sonata["set"].items(), key=lambda x: int(x[0])):
                    # 绘制件数标签
                    draw.text(
                        (col_info["text_x"], current_height),
                        f"{set_num}件:",
                        font=waves_font_16,
                        fill="white",
                    )

                    # 处理效果描述文本
                    desc = effect.get("desc", "")
                    wrapped_desc = textwrap.wrap(desc, width=col_width)

                    # 绘制效果描述
                    for j, line in enumerate(wrapped_desc):
                        draw.text(
                            (col_info["text_x"] + 40, current_height + j * des_height),
                            line,
                            font=waves_font_16,
                            fill="#AAAAAA",
                        )

                    # 更新当前高度
                    current_height += len(wrapped_desc) * des_height + 5

                # 计算当前套装总高度
                sonata_height = current_height - current_y
                max_height = max(max_height, sonata_height)

            # 移动到下一行
            y_offset += max_height + 20

        # 添加组间分隔线
        draw.line((40, y_offset, 1400, y_offset), fill=SPECIAL_GOLD, width=1)
        y_offset += 20

    # 裁剪图片到实际高度
    img = img.crop((0, 0, 1440, y_offset + 50))
    img = add_footer(img, 720, 10)
    return await convert_img(img)


async def draw_echo_list(sonata_type: str):
    # 确保数据已加载
    if not echo_id_data or not set_name_to_echo_ids:
        return "[鸣潮][声骸列表]暂无数据"

    sonata_name = alias_to_sonata_name(sonata_type)
    logger.debug(f"正在处理声骸套装类型：{sonata_name}")

    temp_cost = {0: "1", 1: "3", 2: "4", 3: "4"}

    # 收集声骸数据
    echoes = []
    if sonata_name and sonata_name in set_name_to_echo_ids:
        # 如果指定了套装类型，只收集该套装类型的声骸
        target_set = sonata_name
        echo_ids = set_name_to_echo_ids[target_set]

        for echo_id in echo_ids:
            echo_str_id = str(echo_id)
            if echo_str_id in echo_id_data:
                data = echo_id_data[echo_str_id]
                name = data.get("name", "未知声骸")
                name = name.replace("·", " ").replace("（", " ").replace("）", "")
                name = get_short_name(echo_id, name)
                intensity_code = data.get("intensityCode", 0)
                if "异相" in name:
                    continue  # 排除异相声骸

                echoes.append(
                    {
                        "id": echo_id,
                        "name": name,
                        "intensity_code": intensity_code,
                    }
                )
    else:
        # 如果没有指定套装，显示所有声骸
        for echo_str_id, data in echo_id_data.items():
            echo_id = int(echo_str_id)
            name = data.get("name", "未知声骸")
            name = name.replace("·", " ").replace("（", " ").replace("）", "")
            name = get_short_name(echo_id, name)
            intensity_code = data.get("intensityCode", 0)
            if "异相" in name:
                continue  # 排除异相声骸

            echoes.append(
                {
                    "id": echo_id,
                    "name": name,
                    "intensity_code": intensity_code,
                }
            )

    # 按intensity_code降序排序（值越大越稀有），相同intensity_code时按名称升序
    echoes.sort(key=lambda x: (-x["intensity_code"], x["id"]))

    # 按intensity_code分组
    grouped_echoes = defaultdict(list)
    for echo in echoes:
        grouped_echoes[echo["intensity_code"]].append(echo)

    # 按intensity_code降序排序分组
    sorted_groups = sorted(grouped_echoes.items(), key=lambda x: -x[0])

    # 根据是否指定套装类型决定列数
    if sonata_name and sonata_name in set_name_to_echo_ids:
        # 指定套装时使用4列（参考武器列表）
        echoes_per_row = 4
        icon_size = 120  # 图标大小（参考武器列表）
        horizontal_spacing = 150  # 水平间距（参考武器列表）
        # 计算图片宽度（4列布局）
        width = horizontal_spacing * (echoes_per_row - 1) + icon_size + 80
    else:
        # 未指定套装时使用10列
        echoes_per_row = 10
        icon_size = 100
        horizontal_spacing = 115
        # 计算图片宽度（10列布局）
        width = horizontal_spacing * (echoes_per_row - 1) + icon_size + 80

    # 创建一个足够高的临时图片，最后再裁剪
    img = get_waves_bg(width, 4000, "bg5")
    draw = ImageDraw.Draw(img)

    # 绘制标题
    if sonata_name and sonata_name in set_name_to_echo_ids:
        title = f"套装 {sonata_name} 声骸一览"
        subtitle = f"使用【{PREFIX}'声骸名'介绍】查询具体信息"
    else:
        title = "全部声骸一览"
        subtitle = f"使用【{PREFIX}'套装名'声骸列表】查看指定套装声骸、【{PREFIX}'声骸名'介绍】查询声骸具体信息"

    draw.text((int(width / 2), 25), title, font=waves_font_36, fill=SPECIAL_GOLD, anchor="mt")
    draw.text(
        (int(width / 2), 63),
        subtitle,
        font=waves_font_24,
        fill="#AAAAAA",
        anchor="mt",
    )

    # 当前绘制位置
    y_offset = 90

    # 添加顶部分隔线
    draw.line((40, y_offset, width - 40, y_offset), fill=SPECIAL_GOLD, width=1)
    y_offset += 20

    # 按稀有度分组绘制
    for intensity_code, echoes_in_group in sorted_groups:
        # 绘制稀有度标题
        intensity_color = (
            "#FFD700"
            if intensity_code >= 3
            else "#4169E1"
            if intensity_code == 2
            else "#32CD32"
            if intensity_code == 1
            else "#C0C0C0"
        )
        draw.text(
            (50, y_offset),
            f"cost {temp_cost[intensity_code]} （{len(echoes_in_group)}个）",
            font=waves_font_24,
            fill=intensity_color,
        )
        y_offset += 40

        # 计算该组需要的行数
        rows = (len(echoes_in_group) + echoes_per_row - 1) // echoes_per_row
        name_height = 25
        row_height = icon_size + name_height + 20

        # 绘制该稀有度组内的声骸
        for row in range(rows):
            row_y = y_offset  # 当前行起始位置

            # 绘制该行所有声骸
            for col in range(echoes_per_row):
                index = row * echoes_per_row + col
                if index >= len(echoes_in_group):
                    break

                echo = echoes_in_group[index]

                # 计算位置（居中布局）
                x_pos = 40 + col * horizontal_spacing

                # 获取声骸图标
                echo_icon = await get_phantom_img(echo["id"], "")
                echo_icon = echo_icon.resize((icon_size, icon_size))

                # 合并图标
                img.alpha_composite(echo_icon, (x_pos, row_y))

                # 绘制声骸名称（可能需要截断长名称）
                display_name = echo["name"]
                # 根据列数决定名称截断长度
                max_length = 6 if echoes_per_row >= 8 else 8  # 列数多时截断更短
                if len(display_name) > max_length:
                    display_name = display_name[:max_length] + "..."

                draw.text(
                    (x_pos + icon_size // 2, row_y + icon_size + 10),
                    display_name,
                    font=waves_font_18 if echoes_per_row == 4 else waves_font_16,
                    fill="white",
                    anchor="mt",
                )

            # 移动到下一行
            y_offset += row_height

        # 组间增加间距
        y_offset += 10

        # 添加组间分隔线
        draw.line((40, y_offset, width - 40, y_offset), fill=SPECIAL_GOLD, width=1)
        y_offset += 20

    # 裁剪图片到实际高度
    img = img.crop((0, 0, width, y_offset + 50))
    img = add_footer(img, int(width / 2), 10)  # 页脚居中
    return await convert_img(img)
