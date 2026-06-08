from io import BytesIO
import math
from pathlib import Path

from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.utils import sget
from PIL import Image, ImageDraw

from ..utils import hint
from ..utils.api.model import (
    AccountBaseInfo,
    AreaInfo,
    ExploreArea,
    ExploreItem,
    ExploreList,
)
from ..utils.error_reply import WAVES_CODE_102
from ..utils.fonts.waves_fonts import (
    waves_font_24,
    waves_font_25,
    waves_font_26,
    waves_font_30,
    waves_font_36,
    waves_font_42,
)
from ..utils.image import (
    GOLD,
    GREY,
    WAVES_FREEZING,
    WAVES_LINGERING,
    WAVES_MOLTEN,
    WAVES_MOONLIT,
    WAVES_SIERRA,
    WAVES_SINKING,
    WAVES_VOID,
    YELLOW,
    add_footer,
    change_color,
    get_waves_bg,
)
from ..utils.imagetool import draw_pic_with_ring
from ..utils.waves_api import waves_api

TEXT_PATH = Path(__file__).parent / "texture2d"

tag_yes = Image.open(TEXT_PATH / "tag_yes.png")
tag_yes_draw = ImageDraw.Draw(tag_yes)
tag_yes_draw.text((85, 30), "已完成", "white", waves_font_36, "mm")
tag_no = Image.open(TEXT_PATH / "tag_no.png")
tag_no_draw = ImageDraw.Draw(tag_no)
tag_no_draw.text((85, 30), "未完成", "white", waves_font_36, "mm")

country_color_map = {
    "黑海岸": (28, 55, 118),
    "瑝珑": (140, 113, 58),
    "黎那汐塔": (95, 52, 39),
}

progress_color = [
    (10, WAVES_MOONLIT),
    (20, WAVES_LINGERING),
    (35, WAVES_FREEZING),
    (50, WAVES_SIERRA),
    (70, WAVES_SINKING),
    (80, WAVES_VOID),
    (90, YELLOW),
    (100, WAVES_MOLTEN),
]


def get_progress_color(progress):
    float_progress = float(progress)
    result = WAVES_MOONLIT
    for _p, color in progress_color:
        if float_progress >= _p:
            result = color
    return result

async def draw_explore_img(ev: Event, uid: str, user_id: str):
    is_self_ck, ck = await waves_api.get_ck_result(uid, user_id, ev.bot_id)
    if not ck:
        return hint.error_reply(WAVES_CODE_102)
    # 账户数据
    account_info = await waves_api.get_base_info(uid, ck)
    if not account_info.success:
        return account_info.throw_msg()
    account_info = AccountBaseInfo.model_validate(account_info.data)

    explore_data = await waves_api.get_explore_data(uid, ck)
    if not explore_data.success:
        return explore_data.throw_msg()
    explore_data = ExploreList.model_validate(explore_data.data)
    if not is_self_ck and not explore_data.open:
        return hint.error_reply(msg="探索数据未开启")
    if not explore_data.exploreList:
        return hint.error_reply(msg="探索数据为空")

    # ==================== 布局常量 ====================
    base_info_h = 250          # 头部基础信息区高度
    footer_h = 150             # 底部页脚高度
    explore_title_h = 200      # 每个大区域标题区高度
    explore_frame_h = 500      # 每个小区域框高度（每行3个）
    W = 1900                   # 每个大区域所占宽度（含内部左右边距）
    left_margin = 100          # 图片左边缘到第一列内容左边缘的距离
    right_margin = 100         # 最后一列内容右边缘到图片右边缘的距离
    column_gap = 50            # 列间距

    # 计算每个大区域的高度（标题 + 小区域行数 * 每行高度）
    explore_heights = []
    for _explore in explore_data.exploreList:
        area_count = len(_explore.areaInfoList or [])
        rows = math.ceil(area_count / 3)
        height = explore_title_h + rows * explore_frame_h
        explore_heights.append(height)

    if not explore_heights:
        return hint.error_reply(msg="探索数据为空")

    # ==================== 自动选择最佳列数 ====================
    def calc_layout(k):
        # 贪心将大区域分配到各列（高度大的优先放入当前最矮的列）
        columns = [[] for _ in range(k)]
        col_heights = [0] * k
        sorted_idx = sorted(range(len(explore_heights)), key=lambda i: explore_heights[i], reverse=True)
        for idx in sorted_idx:
            min_col = col_heights.index(min(col_heights))
            columns[min_col].append(idx)
            col_heights[min_col] += explore_heights[idx]
        total_h = base_info_h + max(col_heights) + footer_h
        total_w = left_margin + k * W + (k - 1) * column_gap + right_margin
        return columns, col_heights, total_h, total_w

    best_k = 1
    best_score = float('inf')
    max_allowed_width = 4200  # 最大宽度限制（避免图片过宽）
    for k in range(1, min(4, len(explore_heights) + 1)):
        _, _, total_h, total_w = calc_layout(k)
        # 综合评分：宽高比接近1（方形） + 惩罚过大尺寸
        ratio = max(total_w, total_h) / min(total_w, total_h)
        size_penalty = max(total_w, total_h) / 2000  # 基准2000，越大惩罚越高
        score = ratio + size_penalty
        if total_w > max_allowed_width:
            score += 10  # 超过宽度限制严重惩罚
        if score < best_score:
            best_score = score
            best_k = k

    # 使用最佳列数重新布局
    columns, col_heights, total_height, total_width = calc_layout(best_k)

    # ==================== 创建背景图片 ====================
    img = get_waves_bg(total_width, total_height, "bg3")

    # ==================== 绘制头部固定区域 ====================
    # 头像部分
    avatar, avatar_ring = await draw_pic_with_ring(ev)
    img.paste(avatar, (85, 70), avatar)
    img.paste(avatar_ring, (95, 80), avatar_ring)

    # 基础信息（名字、特征码）
    base_info_bg = Image.open(TEXT_PATH / "base_info_bg.png")
    base_info_draw = ImageDraw.Draw(base_info_bg)
    base_info_draw.text((275, 120), f"{account_info.name[:7]}", "white", waves_font_30, "lm")
    base_info_draw.text((226, 173), f"特征码:  {account_info.id}", GOLD, waves_font_25, "lm")
    img.paste(base_info_bg, (75, 20), base_info_bg)

    # 账号等级 / 世界等级（如果有）
    if account_info.is_full:
        title_bar = Image.open(TEXT_PATH / "title_bar.png")
        title_bar_draw = ImageDraw.Draw(title_bar)
        title_bar_draw.text((660, 125), "账号等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((660, 78), f"Lv.{account_info.level}", "white", waves_font_42, "mm")
        title_bar_draw.text((810, 125), "世界等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((810, 78), f"Lv.{account_info.worldLevel}", "white", waves_font_42, "mm")
        img.paste(title_bar, (40, 70), title_bar)

    # ==================== 绘制各列中的大区域 ====================
    # 预加载可复用的图片模板
    explore_title_template = Image.open(TEXT_PATH / "explore_title.png")
    explore_frame_template = Image.open(TEXT_PATH / "explore_frame.png")
    explore_bar_template = Image.open(TEXT_PATH / "explore_bar.png")
    tag_yes_img = tag_yes   # 外部已定义的100%标签
    tag_no_img = tag_no

    for col_idx, col_indices in enumerate(columns):
        col_x = left_margin + col_idx * (W + column_gap)
        y_offset = base_info_h

        for region_idx in col_indices:
            _explore = explore_data.exploreList[region_idx]

            # ----- 1. 绘制大区域标题 -----
            _explore_title = explore_title_template.copy()
            _explore_title = await change_color(_explore_title, country_color_map.get(_explore.country.countryName, YELLOW))
            # 国家图标
            icon_data = await sget(_explore.country.homePageIcon)
            content_img = Image.open(BytesIO(icon_data.content)).convert("RGBA")
            _explore_title.alpha_composite(content_img, (150, 30))
            # 文字
            _explore_title_draw = ImageDraw.Draw(_explore_title)
            _explore_title_draw.text((370, 100), f"{_explore.country.countryName}", "white", waves_font_42, "lm")
            _explore_title_draw.text((370, 150), f"探索度: {_explore.countryProgress}%", "white", waves_font_42, "lm")
            tag = tag_yes_img if float(_explore.countryProgress) == 100 else tag_no_img
            _explore_title.alpha_composite(tag, (1740, 60))
            # 粘贴标题
            img.alpha_composite(_explore_title, (col_x, y_offset))

            # ----- 2. 绘制小区域（每行3个）-----
            area_list = _explore.areaInfoList or []
            for ni, _subArea in enumerate(area_list):
                row = ni // 3
                col_in_region = ni % 3
                frame_x = col_x + 100 + 600 * col_in_region   # 内部偏移 100+600*列
                frame_y = y_offset + explore_title_h + row * explore_frame_h

                # 复制并定制单个小区域框
                _explore_frame = explore_frame_template.copy()
                _explore_frame = await change_color(_explore_frame, get_progress_color(_subArea.areaProgress), h=83)
                _explore_frame_draw = ImageDraw.Draw(_explore_frame)

                # 区域名称和总进度
                _explore_frame_draw.text((30, 50), f"{_subArea.areaName}", "white", waves_font_36, "lm")
                _explore_frame_draw.text((570, 50), f"{_subArea.areaProgress}%", "white", waves_font_36, "rm")

                # 子项目列表（每个子项目一个进度条）
                max_len = 357
                for bi, _item in enumerate(_subArea.itemList):
                    _explore_bar = explore_bar_template.copy()
                    _explore_frame.alpha_composite(_explore_bar, (20, 90 + 70 * bi))
                    ratio = _item.progress * 0.01
                    # 进度条填充
                    _explore_frame_draw.rounded_rectangle(
                        (131, 113 + 70 * bi, int(131 + ratio * max_len), 126 + 70 * bi),
                        radius=10,
                        fill=get_progress_color(_item.progress),
                    )
                    # 子项名称（折行处理）
                    if len(_item.name) >= 4:
                        s = len(_item.name) // 2
                        _explore_frame_draw.text((68, 95 + 70 * bi), f"{_item.name[:s]}", "white", waves_font_24, "mm")
                        _explore_frame_draw.text((68, 125 + 70 * bi), f"{_item.name[s:]}", "white", waves_font_24, "mm")
                    else:
                        _explore_frame_draw.text((68, 120 + 70 * bi), f"{_item.name}", "white", waves_font_30, "mm")
                    _explore_frame_draw.text((580, 120 + 70 * bi), f"{_item.progress}%", "white", waves_font_30, "rm")

                # 粘贴小区域框
                img.alpha_composite(_explore_frame, (frame_x, frame_y))

            # 更新该列的垂直偏移
            rows_count = math.ceil(len(area_list) / 3)
            y_offset += explore_title_h + rows_count * explore_frame_h

    # ==================== 添加页脚 ====================
    img = add_footer(img, total_width // 2)
    img = img.resize((img.width // 2, img.height // 2), Image.Resampling.LANCZOS)
    img = await convert_img(img)
    return img
