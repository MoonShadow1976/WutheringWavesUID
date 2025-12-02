import asyncio
import copy
import httpx
from pathlib import Path
from typing import Optional, Union

from PIL import Image, ImageDraw

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img

from ..utils.api.wwapi import (
    GET_GACHA_RANK_URL,
    GachaRankData,
    GachaRankItem,
    GachaRankRes,
)
from ..utils.cache import TimedCache
from ..utils.fonts.waves_fonts import (
    waves_font_12,
    waves_font_14,
    waves_font_16,
    waves_font_18,
    waves_font_20,
    waves_font_24,
    waves_font_28,
    waves_font_30,
    waves_font_34,
    waves_font_40,
    waves_font_58,
)
from ..utils.image import (
    AMBER,
    GREY,
    RED,
    SPECIAL_GOLD,
    WAVES_FREEZING,
    WAVES_LINGERING,
    WAVES_MOLTEN,
    WAVES_MOONLIT,
    WAVES_SIERRA,
    WAVES_VOID,
    add_footer,
    get_ICON,
    get_qq_avatar,
    get_square_avatar,
    get_waves_bg,
)
from ..utils.util import get_version
from ..wutheringwaves_config import WutheringWavesConfig
from ..wutheringwaves_analyzecard.user_info_utils import get_region_for_rank

TEXT_PATH = Path(__file__).parent / "texture2d"
avatar_mask = Image.open(TEXT_PATH / "avatar_mask.png")
bar1_img = Image.open(TEXT_PATH / "bar1.png")
pic_cache = TimedCache(86400, 200)

BOT_COLOR = [
    WAVES_MOLTEN,
    AMBER,
    WAVES_VOID,
    WAVES_SIERRA,
    WAVES_FREEZING,
    WAVES_LINGERING,
    WAVES_MOONLIT,
]


async def get_gacha_rank(
    rank_type: str,
    page: int = 1,
    page_num: int = 20,
    waves_id: str = "",
) -> Optional[GachaRankRes]:
    """
    获取抽卡排行数据
    
    Args:
        rank_type: 排行类型
            - character_event: 角色精准调谐排行（按平均UP）
            - weapon_event: 武器精准调谐排行（按平均出金）
            - lucky_rank: 欧皇榜（按最多连续UP）
            - unlucky_rank: 非酋榜（按最多连续非UP）
        page: 页码
        page_num: 每页数量
        waves_id: 用户特征码（可选）
    
    Returns:
        GachaRankRes: 排行榜数据，失败返回None
    """
    WavesToken = WutheringWavesConfig.get_config("WavesToken").data
    
    if not WavesToken:
        return None
    
    # 构建请求参数
    item = GachaRankItem(
        page=page,
        page_num=page_num,
        waves_id=waves_id,
        version=get_version(),
        rank_type=rank_type,
    )
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                GET_GACHA_RANK_URL,
                json=item.dict(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {WavesToken}",
                },
                timeout=httpx.Timeout(30),
            )
            
            if res.status_code == 200:
                return GachaRankRes.model_validate(res.json())
            else:
                return None
                
        except Exception as e:
            return None


async def draw_gacha_server_rank_img(
    bot: Bot, ev: Event, rank_type: str
) -> Union[str, bytes]:
    """
    绘制抽卡排行榜图片
    
    Args:
        bot: 机器人实例
        ev: 事件对象
        rank_type: 排行类型
            - "ww抽卡总排行": 角色精准调谐排行（按平均UP）
            - "ww武器抽卡总排行": 武器精准调谐排行（按平均出金）
            - "ww连金榜": 连金榜（按最多连续UP）
            - "ww连歪榜": 连歪榜（按最多连续非UP）
    """
    # 映射排行类型到API参数
    rank_type_map = {
        "抽卡总排行": "character_event",
        "武器抽卡总排行": "weapon_event",
        "连金榜": "lucky_rank",
        "连歪榜": "unlucky_rank",
    }
    
    # 清理rank_type，去除可能的空格和特殊字符
    rank_type_clean = rank_type.strip()
    
    api_rank_type = rank_type_map.get(rank_type_clean)
    if not api_rank_type:
        return f"未知的排行类型: {rank_type_clean}"
    
    # 获取用户的waves_id（如果有绑定）
    from ..utils.database.models import WavesBind
    waves_id = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
    if not waves_id:
        waves_id = ""
    
    # 获取排行数据
    rank_data = await get_gacha_rank(
        rank_type=api_rank_type,
        page=1,
        page_num=20,
        waves_id=waves_id,
    )
    
    if not rank_data:
        return f"获取{rank_type_clean}排行失败"
    
    if not rank_data.data or not rank_data.data.rank_list:
        return f"{rank_type_clean}暂无数据"
    
    # 绘制排行榜
    return await draw_rank_card(ev, rank_data, rank_type_clean, waves_id)


async def draw_rank_card(
    ev: Event,
    rank_data,
    rank_type: str,
    user_waves_id: str,
) -> bytes:
    """绘制排行卡片 - 采用练度总排行风格"""
    rank_list = rank_data.data.rank_list
    
    # 如果用户不在前20，且服务器返回了用户排名信息，添加到列表末尾
    user_rank_info = None
    if hasattr(rank_data.data, 'user_rank') and rank_data.data.user_rank:
        user_rank_info = rank_data.data.user_rank
        rank_list = list(rank_list) + [user_rank_info]
    
    # 设置图像尺寸
    width = 1300
    text_bar_height = 130
    item_spacing = 120
    header_height = 510
    footer_height = 50
    char_list_len = len(rank_list)
    
    # 计算所需的总高度
    total_height = (
        header_height + text_bar_height + item_spacing * char_list_len + footer_height
    )
    
    # 创建带背景的画布 - 使用bg9
    card_img = get_waves_bg(width, total_height, "bg9")
    
    # 绘制说明栏
    text_bar_img = Image.new("RGBA", (width, 130), color=(0, 0, 0, 0))
    text_bar_draw = ImageDraw.Draw(text_bar_img)
    # 绘制深灰色背景
    bar_bg_color = (36, 36, 41, 230)
    text_bar_draw.rounded_rectangle(
        [20, 20, width - 40, 110], radius=8, fill=bar_bg_color
    )
    
    # 绘制顶部的金色高亮线
    accent_color = (203, 161, 95)
    text_bar_draw.rectangle([20, 20, width - 40, 26], fill=accent_color)
    
    # 左侧标题
    text_bar_draw.text((40, 60), "排行说明", GREY, waves_font_28, "lm")
    
    # 说明文字 - 根据排行类型调整
    subtitle_map = {
        "抽卡总排行": "角色精准调谐，按平均UP抽数排序",
        "武器抽卡总排行": "武器精准调谐，按平均出金抽数排序",
        "连金榜": "角色精准调谐，按最多连续UP次数排序",
        "连歪榜": "角色精准调谐，按最多连续歪次数排序",
    }
    # 上榜条件（仅角色池和武器池显示）
    condition_map = {
        "抽卡总排行": "上榜条件: UP池总抽数≥300",
        "武器抽卡总排行": "上榜条件: 武器池总抽数≥200",
    }
    desc_text = subtitle_map.get(rank_type, "Bot全服排行")
    condition_text = condition_map.get(rank_type, "")
    
    text_bar_draw.text(
        (185, 50),
        f"1. {desc_text}",
        SPECIAL_GOLD,
        waves_font_20,
        "lm",
    )
    if condition_text:  # 只有有条件时才显示第二行
        text_bar_draw.text(
            (185, 85), f"2. {condition_text}", SPECIAL_GOLD, waves_font_20, "lm"
        )
    
    card_img.alpha_composite(text_bar_img, (0, header_height))
    
    # 导入必要的图片资源
    bar = Image.open(TEXT_PATH / "bar1.png")
    
    # 获取头像
    details = rank_list
    tasks = [get_user_avatar(detail.user_id) for detail in details]
    results = await asyncio.gather(*tasks)
    
    # bot颜色映射
    bot_color_map = {}
    bot_color = copy.deepcopy(BOT_COLOR)
    
    # 绘制排行条目
    for rank_temp_index, temp in enumerate(zip(details, results)):
        detail, role_avatar = temp
        y_pos = header_height + 130 + rank_temp_index * item_spacing
        
        # 创建条目背景
        bar_bg = bar.copy()
        bar_bg.paste(role_avatar, (100, 0), role_avatar)
        bar_draw = ImageDraw.Draw(bar_bg)
        
        # 绘制区服标签（在头像右上角）
        region_name, region_color = get_region_for_rank(detail.waves_id)
        region_tag = Image.new("RGBA", (50, 24), color=(255, 255, 255, 0))
        region_tag_draw = ImageDraw.Draw(region_tag)
        region_tag_draw.rounded_rectangle(
            [0, 0, 50, 24], radius=4, fill=region_color + (int(0.85 * 255),)
        )
        region_tag_draw.text((25, 12), region_name, "white", waves_font_14, "mm")
        bar_bg.alpha_composite(region_tag, (180, 20))
        
        # 绘制排名 - 参考角色总排行的实现
        rank_id = detail.rank
        rank_color = (54, 54, 54)
        if rank_id == 1:
            rank_color = (255, 0, 0)
        elif rank_id == 2:
            rank_color = (255, 180, 0)
        elif rank_id == 3:
            rank_color = (185, 106, 217)
        
        # 根据排名范围动态调整尺寸和字体
        if rank_id > 999:
            rank_size = (60, 50)
            rank_font = waves_font_24
            rank_text = "999+"
        elif rank_id > 99:
            rank_size = (60, 50)
            rank_font = waves_font_28
            rank_text = str(rank_id)
        elif rank_id > 9:
            rank_size = (55, 50)
            rank_font = waves_font_34
            rank_text = str(rank_id)
        else:
            rank_size = (50, 50)
            rank_font = waves_font_34
            rank_text = str(rank_id)
        
        # 排名背景
        info_rank = Image.new("RGBA", rank_size, color=(255, 255, 255, 0))
        rank_draw = ImageDraw.Draw(info_rank)
        rank_draw.rounded_rectangle(
            [0, 0, rank_size[0], rank_size[1]], radius=8, fill=rank_color + (int(0.9 * 255),)
        )
        rank_draw.text((rank_size[0] // 2, rank_size[1] // 2), rank_text, "white", rank_font, "mm")
        bar_bg.alpha_composite(info_rank, (40, 35))
        
        # 绘制玩家名字
        bar_draw.text((210, 75), f"{detail.kuro_name}", "white", waves_font_20, "lm")
        
        # uid
        uid_color = "white"
        if detail.waves_id == user_waves_id:
            uid_color = RED
        bar_draw.text(
            (350, 40), f"特征码: {detail.waves_id}", uid_color, waves_font_20, "lm"
        )
        
        # bot主人名字
        botName = getattr(detail, "alias_name", None)
        if botName:
            color = (54, 54, 54)
            if botName in bot_color_map:
                color = bot_color_map[botName]
            elif bot_color:
                color = bot_color.pop(0)
                bot_color_map[botName] = color
            
            info_block = Image.new("RGBA", (200, 30), color=(255, 255, 255, 0))
            info_block_draw = ImageDraw.Draw(info_block)
            info_block_draw.rounded_rectangle(
                [0, 0, 200, 30], radius=6, fill=color + (int(0.6 * 255),)
            )
            info_block_draw.text(
                (100, 15), f"bot: {botName}", "white", waves_font_18, "mm"
            )
            bar_bg.alpha_composite(info_block, (350, 66))
        
        # 数据显示 - 根据排行类型
        if rank_type == "抽卡总排行":
            # 平均UP
            avg_up = detail.avg_up
            up_color = SPECIAL_GOLD if avg_up <= 70 else "white" if avg_up <= 85 else RED
            bar_draw.text((700, 35), f"{avg_up:.1f}", up_color, waves_font_34, "mm")
            bar_draw.text((700, 70), "平均UP", GREY, waves_font_16, "mm")
            
            # 平均出金
            avg_gold = detail.avg_gold
            gold_color = SPECIAL_GOLD if avg_gold <= 60 else "white"
            bar_draw.text((840, 35), f"{avg_gold:.1f}", gold_color, waves_font_30, "mm")
            bar_draw.text((840, 70), "平均出金", GREY, waves_font_16, "mm")
            
            # 总抽数
            total_pulls = detail.total_pulls
            pulls_color = SPECIAL_GOLD if total_pulls >= 1000 else "white"
            bar_draw.text((980, 35), f"{total_pulls}", pulls_color, waves_font_30, "mm")
            bar_draw.text((980, 70), "总抽数", GREY, waves_font_16, "mm")
            
            # 评价
            evaluation = get_character_evaluation(avg_up)
            eval_color = SPECIAL_GOLD if "欧" in evaluation else RED if "非" in evaluation else "white"
            bar_draw.text((1130, 55), evaluation, eval_color, waves_font_24, "mm")
            
        elif rank_type == "武器抽卡总排行":
            # 平均出金
            avg_gold = detail.avg_gold
            gold_color = SPECIAL_GOLD if avg_gold <= 50 else "white" if avg_gold <= 65 else RED
            bar_draw.text((770, 35), f"{avg_gold:.1f}", gold_color, waves_font_34, "mm")
            bar_draw.text((770, 70), "平均出金", GREY, waves_font_16, "mm")
            
            # 总抽数
            total_pulls = detail.total_pulls
            pulls_color = SPECIAL_GOLD if total_pulls >= 500 else "white"
            bar_draw.text((980, 35), f"{total_pulls}", pulls_color, waves_font_30, "mm")
            bar_draw.text((980, 70), "总抽数", GREY, waves_font_16, "mm")
            
            # 评价
            evaluation = get_weapon_evaluation(avg_gold)
            eval_color = SPECIAL_GOLD if "欧" in evaluation else RED if "非" in evaluation else "white"
            bar_draw.text((1130, 55), evaluation, eval_color, waves_font_24, "mm")
            
        elif rank_type == "连金榜":
            # 连金（连续UP）
            max_up = detail.max_consecutive_up
            up_color = SPECIAL_GOLD if max_up >= 3 else "white"
            bar_draw.text((700, 35), f"{max_up}", up_color, waves_font_40, "mm")
            bar_draw.text((700, 70), "连金", GREY, waves_font_16, "mm")
            
            # 平均UP
            avg_up = detail.avg_up
            bar_draw.text((840, 35), f"{avg_up:.1f}", "white", waves_font_30, "mm")
            bar_draw.text((840, 70), "平均UP", GREY, waves_font_16, "mm")
            
            # 总抽数
            total_pulls = detail.total_pulls
            pulls_color = SPECIAL_GOLD if total_pulls >= 1000 else "white"
            bar_draw.text((980, 35), f"{total_pulls}", pulls_color, waves_font_30, "mm")
            bar_draw.text((980, 70), "总抽数", GREY, waves_font_16, "mm")
            
            # 评价
            evaluation = get_lucky_evaluation(max_up)
            eval_color = SPECIAL_GOLD if "欧" in evaluation else "white"
            bar_draw.text((1130, 55), evaluation, eval_color, waves_font_24, "mm")
            
        else:  # 连歪榜
            # 连歪
            max_non_up = detail.max_consecutive_non_up
            non_up_color = RED if max_non_up >= 3 else "white"
            bar_draw.text((700, 35), f"{max_non_up}", non_up_color, waves_font_40, "mm")
            bar_draw.text((700, 70), "连歪", GREY, waves_font_16, "mm")
            
            # 平均UP
            avg_up = detail.avg_up
            bar_draw.text((840, 35), f"{avg_up:.1f}", "white", waves_font_30, "mm")
            bar_draw.text((840, 70), "平均UP", GREY, waves_font_16, "mm")
            
            # 总抽数
            total_pulls = detail.total_pulls
            pulls_color = SPECIAL_GOLD if total_pulls >= 1000 else "white"
            bar_draw.text((980, 35), f"{total_pulls}", pulls_color, waves_font_30, "mm")
            bar_draw.text((980, 70), "总抽数", GREY, waves_font_16, "mm")
            
            # 评价
            evaluation = get_unlucky_evaluation(max_non_up)
            eval_color = RED if "非" in evaluation else "white"
            bar_draw.text((1130, 55), evaluation, eval_color, waves_font_24, "mm")
        
        # 贴到背景
        card_img.paste(bar_bg, (0, y_pos), bar_bg)
    
    # title
    title_bg = Image.open(TEXT_PATH / "gacha_bg.jpg")
    title_bg = title_bg.crop((0, 0, width, 500))
    
    # icon
    icon = get_ICON()
    icon = icon.resize((128, 128))
    title_bg.paste(icon, (60, 240), icon)
    
    # title
    title_text = f"#{rank_type}"
    title_bg_draw = ImageDraw.Draw(title_bg)
    title_bg_draw.text((220, 290), title_text, "white", waves_font_58, "lm")
    
    # 遮罩
    char_mask = Image.open(TEXT_PATH / "char_mask.png").convert("RGBA")
    # 根据width扩图
    char_mask = char_mask.resize((width, char_mask.height * width // char_mask.width))
    char_mask = char_mask.crop((0, char_mask.height - 500, width, char_mask.height))
    char_mask_temp = Image.new("RGBA", char_mask.size, (0, 0, 0, 0))
    char_mask_temp.paste(title_bg, (0, 0), char_mask)
    
    card_img.paste(char_mask_temp, (0, 0), char_mask_temp)
    
    card_img = add_footer(card_img)
    return await convert_img(card_img)


async def get_user_avatar(user_id: str) -> Image.Image:
    """获取用户头像 - 与练度总排行一致"""
    from ..wutheringwaves_config import WutheringWavesConfig
    
    # 检查user_id 为纯数字
    if user_id and user_id.isdigit():
        if WutheringWavesConfig.get_config("QQPicCache").data:
            pic = pic_cache.get(user_id)
            if not pic:
                pic = await get_qq_avatar(user_id, size=100)
                pic_cache.set(user_id, pic)
        else:
            pic = await get_qq_avatar(user_id, size=100)
            pic_cache.set(user_id, pic)
        pic_temp = crop_center_img(pic, 120, 120)
        
        img = Image.new("RGBA", (180, 180))
        avatar_mask_temp = avatar_mask.copy()
        mask_pic_temp = avatar_mask_temp.resize((120, 120))
        img.paste(pic_temp, (0, -5), mask_pic_temp)
    else:
        default_avatar_char_id = "1505"
        pic = await get_square_avatar(default_avatar_char_id)
        
        pic_temp = Image.new("RGBA", pic.size)
        pic_temp.paste(pic.resize((160, 160)), (10, 10))
        pic_temp = pic_temp.resize((160, 160))
        
        avatar_mask_temp = avatar_mask.copy()
        mask_pic_temp = Image.new("RGBA", avatar_mask_temp.size)
        mask_pic_temp.paste(avatar_mask_temp, (-20, -45), avatar_mask_temp)
        mask_pic_temp = mask_pic_temp.resize((160, 160))
        
        img = Image.new("RGBA", (180, 180))
        img.paste(pic_temp, (0, 0), mask_pic_temp)
    
    return img


def get_character_evaluation(avg_up: float) -> str:
    """获取角色池评价（基于平均UP）"""
    if avg_up <= 0:
        return "暂无数据"
    elif avg_up <= 60:
        return "欧皇降临"
    elif avg_up <= 70:
        return "运气不错"
    elif avg_up <= 80:
        return "平稳保底"
    elif avg_up <= 90:
        return "运气一般"
    else:
        return "非酋本酋"


def get_weapon_evaluation(avg_gold: float) -> str:
    """获取武器池评价"""
    if avg_gold <= 0:
        return "暂无数据"
    elif avg_gold <= 45:
        return "欧狗在此"
    elif avg_gold <= 52:
        return "小欧一把"
    elif avg_gold <= 59:
        return "平稳保底"
    elif avg_gold <= 65:
        return "运气不好"
    else:
        return "非到极致"


def get_lucky_evaluation(max_up: int) -> str:
    """获取连金榜评价（基于最多连续UP）"""
    if max_up <= 0:
        return "暂无数据"
    elif max_up >= 5:
        return "欧皇降临"
    elif max_up >= 4:
        return "运气爆棚"
    elif max_up >= 3:
        return "小欧一把"
    elif max_up >= 2:
        return "运气不错"
    else:
        return "平平无奇"


def get_unlucky_evaluation(max_non_up: int) -> str:
    """获取连歪榜评价（基于最多连续歪）"""
    if max_non_up <= 0:
        return "暂无数据"
    elif max_non_up >= 5:
        return "非酋之王"
    elif max_non_up >= 4:
        return "非到极致"
    elif max_non_up >= 3:
        return "运气不好"
    elif max_non_up >= 2:
        return "小非一把"
    else:
        return "运气不错"


