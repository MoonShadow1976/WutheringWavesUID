import asyncio
from pathlib import Path
from typing import Any

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import get_plugin_available_prefix
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw

from ..utils.api.model import AccountBaseInfo, Period, PeriodDetail, PeriodList
from ..utils.database.models import WavesBind
from ..utils.fonts.waves_fonts import (
    waves_font_20,
    waves_font_24,
    waves_font_30,
    waves_font_36,
)
from ..utils.image import add_footer, get_event_avatar, get_waves_bg
from ..utils.waves_api import waves_api

TEXT_PATH = Path(__file__).parent / "texture2d"


based_w = 750
based_h = 930

# 定义颜色列表
colors = [
    (240, 74, 58),  # 珊瑚红 - 日常挑战
    (255, 165, 0),  # 橙色 - 其他
    (81, 207, 102),  # 明绿色 - 大世界探索
    (155, 122, 127),  # 棕色 - 活动奖励
    (77, 171, 247),  # 天蓝色 - 任务获取
    (34, 184, 207),  # 青蓝色 - 玩法奖励
    (245, 157, 148),  # 粉色 - 海市兑换
]

RESOURCE_TYPE_NAME = {
    1: "贝币",
    2: "星声",
    3: "唤声涡纹",
    4: "浮金&铸潮",
}
RESOURCE_TAB_FILES = {
    1: "tab-coin-bg.png",
    2: "tab-star-bg.png",
    3: "tab-lustrous-bg.png",
    4: "tab-radiant-bg.png",
}
RESOURCE_ROW_ORDER = [
    [2, 4],
    [3, 1],
]

MSG_TOKEN = "特征码登录已全部失效！请使用【{}登录】完成绑定！"
MSG_TOKEN_EXPIRED = "该特征码[{}]登录已失效！请使用【{}登录】完成绑定！"
MSG_NO_PERIOD = "该特征码[{}]没有[{}]简报数据~\n用例：{}星声 3.0版本/12月/上周"
PREFIX = get_plugin_available_prefix("WutheringWavesUID")


def _get_relative_period_node(period_param: str, period_list: PeriodList) -> tuple[str, Period] | None:
    period_param = period_param.strip()
    if period_param in ("本月", "本周"):
        period_type = "month" if period_param == "本月" else "week"
        period_seq = period_list.months if period_type == "month" else period_list.weeks
        if not period_seq:
            return None
        period_seq = sorted(period_seq, key=lambda x: x.index, reverse=True)
        return period_type, period_seq[0]

    count = 0
    for ch in period_param:
        if ch == "上":
            count += 1
        else:
            break
    if count == 0:
        return None

    suffix = period_param[count:]
    if suffix == "月":
        if count > 3:
            return None
        period_seq = period_list.months
        period_type = "month"
    elif suffix == "周":
        if count > 12:
            return None
        period_seq = period_list.weeks
        period_type = "week"
    else:
        return None

    if not period_seq:
        return None

    period_seq = sorted(period_seq, key=lambda x: x.index, reverse=True)
    if count >= len(period_seq):
        return None
    return period_type, period_seq[count]


async def process_uid(uid, ev, period_param: int | str | None) -> dict[str, Any] | str | None:
    ck = await waves_api.get_self_waves_ck(uid, ev.user_id, ev.bot_id)
    if not ck:
        return None

    period_list = await waves_api.get_period_list(uid, ck)
    if not period_list.success or not period_list.data:
        return None

    period_list = PeriodList.model_validate(period_list.data)

    period_type = "month"
    period_node: Period | None = None
    if period_param:
        if isinstance(period_param, str):
            relative = _get_relative_period_node(period_param, period_list)
            if relative:
                period_type, period_node = relative
        if not period_node:
            for period in period_list.months:
                if period.index == period_param or period.title == period_param:
                    period_node = period
                    period_type = "month"
                    break
        if not period_node:
            for period in period_list.weeks:
                if period.index == period_param or period.title == period_param:
                    period_node = period
                    period_type = "week"
                    break
        if not period_node:
            for period in period_list.versions:
                if period.index == period_param or period.title == period_param:
                    period_node = period
                    period_type = "version"
                    break
    elif period_list.versions:
        period_list.versions.sort(key=lambda x: x.index, reverse=True)
        period_node = period_list.versions[0]
        period_type = "version"

    if not period_node:
        return MSG_NO_PERIOD.format(uid, period_param, PREFIX)

    period_detail = await waves_api.get_period_detail(period_type, period_node.index, uid, ck)
    if not period_detail.success or not period_detail.data:
        return None
    period_detail = PeriodDetail.model_validate(period_detail.data)

    account_info = await waves_api.get_base_info(uid, ck)
    if not account_info.success or not account_info.data:
        return None
    account_info = AccountBaseInfo.model_validate(account_info.data)

    return {
        "period_node": period_node,
        "period_detail": period_detail,
        "account_info": account_info,
    }


async def draw_period_img(bot: Bot, ev: Event):
    period_param = ev.text.strip() if ev.text else None
    logger.info(f"[鸣潮][资源简报]绘图开始: {period_param}")
    try:
        uid_list = await WavesBind.get_uid_list_by_game(ev.user_id, ev.bot_id)

        if uid_list is None:
            return MSG_TOKEN.format(PREFIX)

        # 进行校验UID是否绑定CK
        tasks = [process_uid(uid, ev, period_param) for uid in uid_list]
        results = await asyncio.gather(*tasks)

        # 过滤掉 None 值
        valid_period_list = [res for res in results if isinstance(res, dict)]

        if len(valid_period_list) == 0:
            msg = [res for res in results if isinstance(res, str)]
            if msg:
                return "\n".join(msg)
            return MSG_TOKEN.format(PREFIX)

        # 开始绘图任务
        tasks = []

        for uid_index, valid in enumerate(valid_period_list):
            tasks.append(_draw_all_period_img(ev, valid, uid_index))

        # 收集所有生成的图片
        images = await asyncio.gather(*tasks)

        # 计算总高度
        total_height = sum(img.height for img in images)

        # 创建最终的画布
        final_img = Image.new("RGBA", (based_w, total_height), (0, 0, 0, 0))

        # 拼接图片
        current_y = 0
        for img in images:
            final_img.paste(img, (0, current_y))
            current_y += img.height

        res = await convert_img(final_img)
    except TypeError:
        logger.exception("[鸣潮][资源简报]绘图失败!")
        res = "你绑定过的UID中可能存在过期CK~请重新绑定一下噢~"

    return res


async def _draw_all_period_img(ev: Event, valid: dict[str, Any], uid_index: int) -> Image.Image:
    period_img = await _draw_period_img(ev, valid)
    return period_img.convert("RGBA")


async def _draw_period_img(ev: Event, valid: dict):
    period_detail: PeriodDetail = valid["period_detail"]
    account_info: AccountBaseInfo = valid["account_info"]
    period_node: Period = valid["period_node"]

    # 计算布局位置以确定画布大小
    # 计算标签高度
    start_y = 115
    for row in RESOURCE_ROW_ORDER:
        max_h = 0
        for rid in row:
            tab_path = TEXT_PATH / RESOURCE_TAB_FILES[rid]
            # 仅打开以获取尺寸
            with Image.open(tab_path) as tab_img:
                max_h = max(max_h, tab_img.height)
        start_y += max_h

    # 来源部分
    source_gap = 10
    source_y = start_y + source_gap

    # 饼图数据 (用于图例高度计算)
    if period_detail.itemList:
        star_item = get_resource_item_map(period_detail).get(2)
        star_list = []
        if star_item:
            star_list = list(star_item.detail)
            star_list.sort(key=lambda x: x.sort if x.sort is not None else 999)
        total_star = int(star_item.total) if star_item else 0
    else:
        star_list = period_detail.starList
        total_star = int(period_detail.totalStar or 0)

    pie_data_num_map = [(item.type, item.num) for item in star_list]

    legend_height = 75 + len(pie_data_num_map) * 45 + 20
    pie_height = max(350, legend_height)

    # 文案
    copywriting = (period_detail.copyWriting or "").rstrip("。")
    copy_lines = []
    copy_block_height = 0
    if copywriting:
        temp_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        copy_lines = wrap_text(copywriting, waves_font_20, 600, temp_draw)
        line_box = waves_font_20.getbbox("Hg")
        line_height = max(1, line_box[3] - line_box[1])
        if copy_lines:
            copy_block_height = int(len(copy_lines) * line_height + (len(copy_lines) - 1) * 6)

    # 页脚
    footer_height = 35

    copy_start_y = source_y + pie_height + (10 if copy_lines else 0)
    total_home_height = copy_start_y + copy_block_height + footer_height
    # 确保最小高度
    total_home_height = max(total_home_height, 500)

    total_img_height = 235 + total_home_height + 50

    # 创建主画布
    img = get_waves_bg(based_w, total_img_height, bg="bg10")

    # 遮罩
    mask_img = Image.open(TEXT_PATH / "home-mask-black.png").convert("RGBA")
    mask_img = mask_img.crop((0, 0, based_w, total_home_height + 180))
    img.alpha_composite(mask_img, (0, 70))

    # 绘制角色信息 750 × 206
    title_img = Image.open(TEXT_PATH / "top-bg.png")
    title_img_draw = ImageDraw.Draw(title_img)
    title_img_draw.text((240, 75), f"{account_info.name}", "black", waves_font_36, "lm")
    title_img_draw.text((240, 140), f"特征码: {account_info.id}", "black", waves_font_24, "lm")

    avatar_img = await draw_pic_with_ring(ev)
    title_img.paste(avatar_img, (27, 8), avatar_img)

    img.paste(title_img, (0, 30), title_img)

    # 绘制slagon.png
    slagon_img = Image.open(TEXT_PATH / "slagon.png")
    img.paste(slagon_img, (500, 95), slagon_img)

    # 绘制底板
    home_bg = await crop_home_img(total_home_height)

    # topup
    topup_bg = Image.open(TEXT_PATH / "txt-topup.png")
    home_bg.alpha_composite(topup_bg, (0, 60))

    # ico-sourct-tab.png
    icon_source_tab = Image.open(TEXT_PATH / "ico-sourct-tab.png")
    icon_souce_tab_draw = ImageDraw.Draw(icon_source_tab)
    icon_souce_tab_draw.text((77, 25), f"{period_node.title}", "white", waves_font_30, "mm")
    home_bg.paste(icon_source_tab, (500, 60), icon_source_tab)

    # 绘制资源tab
    curr_y = 115
    for row in RESOURCE_ROW_ORDER:
        max_h = 0

        # 左侧 Tab
        if len(row) > 0:
            rid = row[0]
            tab_path = TEXT_PATH / RESOURCE_TAB_FILES[rid]
            tab_img = Image.open(tab_path)
            total = get_resource_total(period_detail, rid)
            name = RESOURCE_TYPE_NAME.get(rid, str(rid))
            tab_img = render_resource_tab(tab_img, name, total)

            home_bg.paste(tab_img, (40, curr_y), tab_img)
            max_h = max(max_h, tab_img.height)

        # 右侧 Tab
        if len(row) > 1:
            rid = row[1]
            tab_path = TEXT_PATH / RESOURCE_TAB_FILES[rid]
            tab_img = Image.open(tab_path)
            total = get_resource_total(period_detail, rid)
            name = RESOURCE_TYPE_NAME.get(rid, str(rid))
            tab_img = render_resource_tab(tab_img, name, total)

            home_bg.paste(tab_img, (380, curr_y), tab_img)
            max_h = max(max_h, tab_img.height)

        curr_y += max_h

    # source
    source_bg = Image.open(TEXT_PATH / "txt-source.png")
    home_bg.alpha_composite(source_bg, (0, source_y))

    # 饼图数据逻辑已在上方完成，用于高度计算
    pie_data = {item.type: (float(item.num / total_star * 100) if total_star else 0) for item in star_list}

    # 获取合成后的饼图
    pie_placeholder = create_pie_chart_with_placeholder(pie_data)
    home_bg.paste(pie_placeholder, (380, source_y + 50), pie_placeholder)

    # 在左侧绘制图例
    draw_legend_on_home_bg(home_bg, pie_data_num_map, 50, source_y + 75)

    # 在图表下方绘制全局文案
    if copy_lines:
        draw = ImageDraw.Draw(home_bg)
        line_box = waves_font_20.getbbox("Hg")
        line_height = max(1, line_box[3] - line_box[1])
        base_y = copy_start_y + (line_height // 2)
        for idx, line in enumerate(copy_lines):
            y = base_y + idx * (line_height + 6)
            draw.text((home_bg.width // 2, y), line, (80, 80, 80), waves_font_20, "mm")

    img.paste(home_bg, (30, 235), home_bg)
    img = add_footer(img, 600, 25)
    return img


async def crop_home_img(target_height: int = 500):
    img = Image.new("RGBA", (718, target_height), (0, 0, 0, 0))

    # 1. 头部: 718*56
    home_main_1 = Image.open(TEXT_PATH / "home-main-p1.png")
    img.paste(home_main_1, (0, 0), home_main_1)

    # 2. 底部: 718*86
    home_main_3 = Image.open(TEXT_PATH / "home-main-p3.png")
    # 粘贴在最底部
    img.paste(home_main_3, (0, target_height - 86), home_main_3)

    # 3. 中间: 使用平铺的 p2 图片实现可变高度
    home_main_2 = Image.open(TEXT_PATH / "home-main-p2.png")  # 718x280
    p2_height = max(1, home_main_2.height - 150)
    home_main_2 = home_main_2.crop((0, 0, home_main_2.width, p2_height))

    # 计算中间区域
    middle_start_y = 56
    middle_end_y = target_height - 86
    middle_height = middle_end_y - middle_start_y

    # 创建中间图片
    middle_img = Image.new("RGBA", (718, middle_height), (0, 0, 0, 0))

    if middle_height <= p2_height:
        p2_crop = home_main_2.crop((0, 0, 718, middle_height))
        middle_img.paste(p2_crop, (0, 0), p2_crop)
    else:
        y = 0
        while y < middle_height:
            remaining = middle_height - y
            if remaining < p2_height:
                p2_crop = home_main_2.crop((0, 0, 718, remaining))
                middle_img.paste(p2_crop, (0, y), p2_crop)
                break
            middle_img.paste(home_main_2, (0, y), home_main_2)
            y += p2_height

    img.paste(middle_img, (0, 56), middle_img)

    return img


def wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for ch in paragraph:
            test = f"{current}{ch}"
            if draw.textlength(test, font=font) <= max_width or not current:
                current = test
            else:
                lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


async def draw_pic_with_ring(ev: Event):
    pic = await get_event_avatar(ev, is_valid_at_param=False)

    mask_pic = Image.open(TEXT_PATH / "avatar_mask.png")
    img = Image.new("RGBA", (200, 200))
    mask = mask_pic.resize((160, 160))
    resize_pic = crop_center_img(pic, 160, 160)
    img.paste(resize_pic, (20, 20), mask)

    return img


def get_resource_item_map(period_detail: PeriodDetail) -> dict[int, Any]:
    if period_detail.itemList:
        return {item.type: item for item in period_detail.itemList}
    return {}


def get_resource_total(period_detail: PeriodDetail, resource_id: int) -> int:
    item_map = get_resource_item_map(period_detail)
    if resource_id in item_map:
        item = item_map[resource_id]
        return int(item.total or 0)
    if resource_id == 2:
        return int(period_detail.totalStar or 0)
    if resource_id == 1:
        return int(period_detail.totalCoin or 0)
    return 0


def render_resource_tab(bg: Image.Image, name: str, total: int) -> Image.Image:
    draw = ImageDraw.Draw(bg)
    name_x = int(bg.width * 0.36)
    name_y = int(bg.height * 0.27)
    value_y = int(bg.height * 0.62)
    draw.text((name_x, name_y), name, "black", waves_font_24, "lm")
    draw.text((name_x, value_y), f"{total}", "black", waves_font_30, "lm")
    return bg


def draw_legend_on_home_bg(
    home_bg: Image.Image,
    pie_data_num_map: list[tuple[str, int]],
    x: int,
    y: int,
):
    draw = ImageDraw.Draw(home_bg)

    for i, (label, value) in enumerate(pie_data_num_map):
        current_y = y + i * 45

        # 绘制颜色圆点
        color = colors[i % len(colors)]
        draw.ellipse([x + 5, current_y + 5, x + 20, current_y + 20], fill=color)

        # 绘制标签
        # percentage = f"{value:.1f}%"
        percentage = f"{value}"
        draw.text((x + 30, current_y + 2), label, fill=(80, 80, 80), font=waves_font_24)
        draw.text((x + 170, current_y + 2), percentage, fill=color, font=waves_font_24)


def draw_pie_chart_for_bg(data_dict: dict[str, float], bg_size: int, outer_radius: int, inner_radius: int) -> Image.Image:
    # 创建透明背景的图片
    img = Image.new("RGBA", (bg_size, bg_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 计算总值
    total = sum(data_dict.values())
    if total == 0:
        return img

    # 计算圆的边界框
    center = bg_size // 2
    outer_bbox = [
        center - outer_radius,
        center - outer_radius,
        center + outer_radius,
        center + outer_radius,
    ]
    inner_bbox = [
        center - inner_radius,
        center - inner_radius,
        center + inner_radius,
        center + inner_radius,
    ]

    # 绘制饼图
    start_angle = -90  # 从顶部开始
    color_index = 0

    for label, value in data_dict.items():
        # 计算角度
        angle = (value / total) * 360
        end_angle = start_angle + angle

        # 绘制扇形
        if angle > 0:
            # 先绘制外圆扇形
            draw.pieslice(
                outer_bbox,
                start_angle,
                end_angle,
                fill=colors[color_index % len(colors)],
                outline=(255, 255, 255, 100),
                width=1,
            )

            # 再绘制内圆来创建圆环效果（使用透明色覆盖）
            draw.pieslice(
                inner_bbox,
                start_angle,
                end_angle,
                fill=(255, 255, 255, 0),  # 透明
            )

        start_angle = end_angle
        color_index += 1

    # 最后绘制内圆的边框
    draw.ellipse(inner_bbox, fill=None, outline=(255, 255, 255, 100), width=1)

    return img


def create_pie_chart_with_placeholder(pie_data: dict[str, float]) -> Image.Image:
    # 加载placeholder背景图
    placeholder = Image.open(TEXT_PATH / "placeholder.png").convert("RGBA")

    # 计算外圆和内圆的半径（根据背景图的比例）
    outer_radius = 120
    inner_radius = 45

    # 创建饼图，使其完全匹配placeholder的圆环
    pie_chart = draw_pie_chart_for_bg(pie_data, 300, outer_radius, inner_radius)

    # 将饼图合成到placeholder上
    placeholder.alpha_composite(pie_chart, (10, 5))

    return placeholder
