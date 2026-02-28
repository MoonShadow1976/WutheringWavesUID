from venv import logger

from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw

from ..utils.ascension.monster import get_all_monster_models
from ..utils.fonts.waves_fonts import (
    waves_font_28,
    waves_font_44,
)
from ..utils.image import (
    SPECIAL_GOLD,
    add_footer,
    get_attribute,
    get_crop_waves_bg,
)
from ..utils.resource.constant import ATTRIBUTE_ID_MAP
from ..utils.resource.download_file import get_monster_img


async def draw_monster_resistance_table(monster_list: dict) -> bytes:
    """
    绘制怪物抗性表
    每个属性列下面垂直排列有该抗性的怪物
    """
    # 获取所有属性并排序（按照属性ID顺序）
    attributes = [ATTRIBUTE_ID_MAP[i] for i in range(7)]

    # 按rarity降序，monster_id（字符串）升序排序怪物
    sorted_monsters = sorted(
        monster_list.items(),
        key=lambda x: (-x[1].rarity, int(x[0])),
    )

    # 按属性分组怪物
    attribute_groups = {attr: [] for attr in attributes}

    for monster_id, monster in sorted_monsters:
        resistances = monster.get_element_resistance()
        for resistance in resistances:
            if resistance in attribute_groups:
                attribute_groups[resistance].append((monster_id, monster))

    # 计算最大怪物数
    max_monster_count = max(len(monsters) for monsters in attribute_groups.values())

    # 单元格尺寸
    column_width = 200  # 每列宽度
    monster_cell_height = 160  # 每个怪物单元格高度
    header_height = 100  # 标题行高度

    # 计算总图片尺寸
    num_columns = len(attributes)
    total_width = num_columns * column_width + 40  # 加边距
    total_height = header_height + (max_monster_count * monster_cell_height) + 240

    # 创建背景
    bg_img = get_crop_waves_bg(total_width, total_height, "bg5")

    # 创建主图片
    main_img = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    main_img.alpha_composite(bg_img, (0, 0))

    draw = ImageDraw.Draw(main_img)

    # 绘制主标题
    draw.text((total_width // 2, 30), "怪物额外属性抗性表", fill=SPECIAL_GOLD, font=waves_font_44, anchor="mm")

    # 绘制描述文字
    description_text = "基础全属性抗性10%，额外属性抗性：大世界30%，深塔50%，全息70%"
    draw.text((total_width // 2, 70), description_text, fill=(200, 200, 200), font=waves_font_28, anchor="mm")

    # 绘制属性列标题
    start_x = 20
    start_y = 110

    # 绘制每个属性列
    for col_idx, attr_name in enumerate(attributes):
        col_x = start_x + col_idx * column_width

        # 绘制属性标题区域
        attr_title_bg = Image.new("RGBA", (column_width, header_height), (0, 0, 0, 100))
        main_img.alpha_composite(attr_title_bg, (col_x, start_y))

        # 获取属性图标
        try:
            attr_icon = await get_attribute(attr_name, is_simple=True)
            attr_icon = attr_icon.resize((110, 110))

            # 居中放置图标：应该是每列居中，不是向左偏移
            icon_x = col_x + (column_width - 110) // 2  # 居中计算
            icon_y = start_y
            main_img.alpha_composite(attr_icon, (icon_x, icon_y))
        except Exception:
            logger.warning(f"获取属性图标失败：{attr_name}")

        # 绘制该属性下的怪物
        monsters_in_attr = attribute_groups[attr_name]

        for row_idx, (monster_id, monster) in enumerate(monsters_in_attr):
            # 计算怪物单元格位置
            cell_y = start_y + header_height + (row_idx * monster_cell_height)

            # 绘制怪物图片
            try:
                echo, echo_exist = monster.get_link_echo()
                monster_img = await get_monster_img(int(monster_id)) if not echo_exist else await get_monster_img(echo, True)
                monster_img = monster_img.resize((100, 100))
                monster_img = crop_center_img(monster_img, 100, 100)  # 保持100x100裁剪

                # 计算图片位置（居中对齐）
                img_x = col_x + (column_width - 100) // 2  # 居中计算
                img_y = cell_y + 25

                main_img.alpha_composite(monster_img, (img_x, img_y))
            except Exception:
                logger.warning(f"获取怪物图片失败：{monster_id}")

            # 绘制怪物名称
            monster_name = monster.name
            # 名称太长则截断
            if len(monster_name) > 8:
                monster_name = monster_name[-7:]  # 取后七个字

            # 名称放在图片底侧居中
            name_x = col_x + column_width // 2  # 列中心
            name_y = cell_y + monster_cell_height - 15

            draw.text((name_x, name_y), monster_name, fill="white", font=waves_font_28, anchor="mm")  # 使用"mm"锚点居中

    # 绘制水平分隔线
    for row_idx in range(max_monster_count + 1):
        line_y = start_y + header_height + (row_idx * monster_cell_height)
        draw.line([(start_x, line_y), (start_x + num_columns * column_width, line_y)], fill=(100, 100, 100, 150), width=2)

    # 添加脚注
    main_img = add_footer(main_img, total_width, 20, color="encore")

    return await convert_img(main_img)


# 如果需要在外部调用，可以添加一个包装函数
async def draw_resist_table(rarity: int = 2):
    """获取怪物抗性表"""
    # 过滤出指定稀有度
    all_monster = get_all_monster_models()
    monster_list = {key: value for key, value in all_monster.items() if value.rarity >= rarity}

    return await draw_monster_resistance_table(monster_list)
