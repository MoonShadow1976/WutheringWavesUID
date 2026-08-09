from pathlib import Path

from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw

from ..utils.api.model import SkinData
from ..utils.fonts.waves_fonts import (
    waves_font_25,
    waves_font_26,
    waves_font_28,
    waves_font_30,
    waves_font_42,
)
from ..utils.image import (
    GOLD,
    GREY,
    add_footer,
    get_waves_bg,
)
from ..utils.imagetool import draw_pic_with_ring
from ..utils.resource.download_file import get_skin_img
from ..utils.resource.RESOURCE_PATH import (
    CALABASH_SKIN_PATH,
    FLY_SKIN_PATH,
    ORNAMENT_SKIN_PATH,
    ROLE_SKIN_PATH,
    WEAPON_SKIN_PATH,
)
from ..utils.waves_api import waves_api

TEXT_PATH = Path(__file__).parent / "texture2d"
BG_TEXTURE_PATH = TEXT_PATH / "bg"


def to_grayscale(img: Image.Image) -> Image.Image:
    """将图片转换为灰度（保留透明度）"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    gray = img.convert("L").convert("RGBA")
    r, g, b, a = img.split()
    _, _, _, a_gray = gray.split()
    gray.putalpha(a)
    return gray


def get_skin_border_frame(quality: int) -> Image.Image | None:
    """获取皮肤边框（501→4）"""
    # 品质归一化：501 视为 4
    if quality == 501:
        quality = 4
    if quality == 5:
        border_path = BG_TEXTURE_PATH / "五星皮肤框.png"
    elif quality == 4:
        border_path = BG_TEXTURE_PATH / "四星皮肤框.png"
    else:
        return None

    if border_path.exists():
        try:
            return Image.open(border_path).convert("RGBA")
        except Exception as e:
            print(f"加载皮肤边框失败: {border_path}, 错误: {e}")
    return None


def get_quality_border(quality: int) -> Image.Image | None:
    """获取品质边框素材（5=金色, 4=紫色, 3=蓝色, 501→4）"""
    # 品质归一化：501 视为 4
    if quality == 501:
        quality = 4
    quality_map = {
        5: "SP_QualitySkinGold.png",
        4: "SP_QualitySkinPurple.png",
        3: "SP_QualitySkinBlue.png",
    }
    if quality not in quality_map:
        return None

    border_path = BG_TEXTURE_PATH / quality_map[quality]
    if border_path.exists():
        try:
            return Image.open(border_path).convert("RGBA")
        except Exception as e:
            print(f"加载品质边框失败: {border_path}, 错误: {e}")
    return None


def draw_section_header(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    title: str,
):
    """绘制带金色装饰条的分区标题"""
    # 金色装饰条
    bar_x, bar_y = x, y + 6
    bar_w, bar_h = 4, 24
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], fill=GOLD)
    # 标题文字
    draw.text((x + 16, y + 18), title, "white", waves_font_28, "lm")


async def draw_skin_img(uid: str, ck: str, ev: Event):
    # 获取皮肤数据
    if waves_api.is_net(uid):
        # 构造空skin_data
        skin_data = SkinData()
    else:
        skin_data_resp = await waves_api.get_skin_data(uid, ck)
        if not skin_data_resp.success:
            return skin_data_resp.throw_msg()

        skin_data = SkinData.model_validate(skin_data_resp.data)

    # 获取账户基本信息
    from ..wutheringwaves_analyzecard.user_info_utils import get_user_detail_info

    account_info = await get_user_detail_info(uid)

    # 按品质排序（品质高的排前面）
    # 角色皮肤：构建完整列表（已拥有 + 未拥有）
    owned_role_skins = []
    owned_role_skin_names = set()
    if skin_data.roleSkinList:
        # 只保留四星和五星的已拥有角色皮肤
        owned_role_skins = [s for s in skin_data.roleSkinList if s.quality >= 4]
        owned_role_skins.sort(key=lambda x: x.quality, reverse=True)
        owned_role_skin_names = {s.skinName for s in owned_role_skins}

    # 获取本地所有角色皮肤名称
    all_local_role_names = []
    if ROLE_SKIN_PATH.exists():
        for f in sorted(ROLE_SKIN_PATH.iterdir()):
            if f.suffix == ".png" and f.stem != "五星皮肤框" and f.stem != "四星皮肤框":
                all_local_role_names.append(f.stem)

    # 找出未拥有的角色皮肤
    unowned_role_names = [name for name in all_local_role_names if name not in owned_role_skin_names]

    # 构建完整角色皮肤列表：已拥有在前，未拥有在后
    all_role_skins = list(owned_role_skins)
    all_role_skins.extend(unowned_role_names)

    # 武器皮肤：构建完整列表（已拥有 + 未拥有）
    owned_weapon_skins = []
    owned_weapon_skin_names = set()
    if skin_data.weaponSkinList:
        owned_weapon_skins = sorted(skin_data.weaponSkinList, key=lambda x: x.quality, reverse=True)
        owned_weapon_skin_names = {s.skinName for s in owned_weapon_skins}

    all_local_weapon_names = []
    if WEAPON_SKIN_PATH.exists():
        for f in sorted(WEAPON_SKIN_PATH.iterdir()):
            if f.suffix == ".png":
                all_local_weapon_names.append(f.stem)

    unowned_weapon_names = [name for name in all_local_weapon_names if name not in owned_weapon_skin_names]
    all_weapon_skins = list(owned_weapon_skins)
    all_weapon_skins.extend(unowned_weapon_names)

    # 终端皮肤：构建完整列表（已拥有 + 未拥有）
    owned_calabash_skins = []
    owned_calabash_skin_names = set()
    if skin_data.calabashSkinList:
        owned_calabash_skins = sorted(skin_data.calabashSkinList, key=lambda x: x.quality, reverse=True)
        owned_calabash_skin_names = {s.skinName for s in owned_calabash_skins}

    all_local_calabash_names = []
    if CALABASH_SKIN_PATH.exists():
        for f in sorted(CALABASH_SKIN_PATH.iterdir()):
            if f.suffix == ".png":
                all_local_calabash_names.append(f.stem)

    unowned_calabash_names = [name for name in all_local_calabash_names if name not in owned_calabash_skin_names]
    all_calabash_skins = list(owned_calabash_skins)
    all_calabash_skins.extend(unowned_calabash_names)

    # 翅膀皮肤：构建完整列表（已拥有 + 未拥有）
    owned_fly_skins = []
    owned_fly_skin_names = set()
    if skin_data.equipSkinList:
        owned_fly_skins = sorted(skin_data.equipSkinList, key=lambda x: x.quality, reverse=True)
        owned_fly_skin_names = {s.skinName for s in owned_fly_skins}

    all_local_fly_names = []
    if FLY_SKIN_PATH.exists():
        for f in sorted(FLY_SKIN_PATH.iterdir()):
            if f.suffix == ".png":
                all_local_fly_names.append(f.stem)

    unowned_fly_names = [name for name in all_local_fly_names if name not in owned_fly_skin_names]
    all_fly_skins = list(owned_fly_skins)
    all_fly_skins.extend(unowned_fly_names)

    # 角色装饰：构建完整列表（已拥有 + 未拥有）
    owned_ornament_skins = []
    owned_ornament_names = set()
    if skin_data.roleDecorationList:
        owned_ornament_skins = sorted(skin_data.roleDecorationList, key=lambda x: x.quality, reverse=True)
        owned_ornament_names = {d.name for d in owned_ornament_skins}

    all_local_ornament_names = []
    if ORNAMENT_SKIN_PATH.exists():
        for f in sorted(ORNAMENT_SKIN_PATH.iterdir()):
            if f.suffix == ".png":
                all_local_ornament_names.append(f.stem)

    unowned_ornament_names = [name for name in all_local_ornament_names if name not in owned_ornament_names]
    all_ornament_skins = list(owned_ornament_skins)
    all_ornament_skins.extend(unowned_ornament_names)

    # 计算需要的画布大小
    calabash_count = len(all_calabash_skins)
    equip_count = len(all_fly_skins)
    decoration_count = len(all_ornament_skins)
    role_skin_count = len(all_role_skins)
    weapon_skin_count = len(all_weapon_skins)

    # 角色皮肤布局参数（保持不变）
    items_per_row = 4
    item_width = 200
    item_height = 580
    gap = 80

    # 其他区域布局参数（重新设计：紧凑卡片式）
    other_items_per_row = 4
    other_item_width = 230
    other_item_height = 220
    other_gap = 40
    other_section_height = 55
    other_left_padding = 80

    header_height = 300

    # 计算各部分行数
    calabash_rows = (calabash_count + other_items_per_row - 1) // other_items_per_row if calabash_count > 0 else 0
    equip_rows = (equip_count + other_items_per_row - 1) // other_items_per_row if equip_count > 0 else 0
    decoration_rows = (decoration_count + other_items_per_row - 1) // other_items_per_row if decoration_count > 0 else 0
    role_skin_rows = (role_skin_count + items_per_row - 1) // items_per_row if role_skin_count > 0 else 0
    weapon_skin_rows = (weapon_skin_count + other_items_per_row - 1) // other_items_per_row if weapon_skin_count > 0 else 0

    total_height = header_height
    if role_skin_count > 0:
        total_height += other_section_height + role_skin_rows * (item_height + gap)
    if weapon_skin_count > 0:
        total_height += other_section_height + weapon_skin_rows * (other_item_height + other_gap)
    if calabash_count > 0:
        total_height += other_section_height + calabash_rows * (other_item_height + other_gap)
    if equip_count > 0:
        total_height += other_section_height + equip_rows * (other_item_height + other_gap)
    if decoration_count > 0:
        total_height += other_section_height + decoration_rows * (other_item_height + other_gap)

    total_height += 180  # 底部留白（含footer空间）

    # 创建画布
    card_width = 1200
    card_img = get_waves_bg(card_width, total_height, bg="bg7")
    draw = ImageDraw.Draw(card_img)

    # 绘制用户基本信息区域
    base_info_bg = Image.open(BG_TEXTURE_PATH / "base_info_bg.png")
    base_info_draw = ImageDraw.Draw(base_info_bg)
    if account_info:
        base_info_draw.text((275, 120), f"{account_info.name[:7]}", "white", waves_font_30, "lm")
        base_info_draw.text((226, 173), f"特征码:  {account_info.id}", GOLD, waves_font_25, "lm")
    else:
        base_info_draw.text((275, 120), f"UID: {uid}", "white", waves_font_30, "lm")
        base_info_draw.text((226, 173), "未绑定CK", GOLD, waves_font_25, "lm")
    card_img.paste(base_info_bg, (35, 20), base_info_bg)

    # 头像和头像环
    avatar, avatar_ring = await draw_pic_with_ring(ev)
    card_img.paste(avatar, (45, 70), avatar)
    card_img.paste(avatar_ring, (55, 80), avatar_ring)

    # 账号等级和世界等级
    if account_info:
        title_bar = Image.open(BG_TEXTURE_PATH / "title_bar.png")
        title_bar_draw = ImageDraw.Draw(title_bar)
        title_bar_draw.text((660, 125), "账号等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((660, 78), f"Lv.{account_info.level or '?'}", "white", waves_font_42, "mm")
        title_bar_draw.text((810, 125), "世界等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((810, 78), f"Lv.{account_info.worldLevel or '?'}", "white", waves_font_42, "mm")
        card_img.paste(title_bar, (0, 70), title_bar)

    current_y = header_height

    # 绘制角色皮肤
    if all_role_skins:
        draw_section_header(draw, other_left_padding, current_y, "角色皮肤")
        current_y += other_section_height + 30

        for i, skin in enumerate(all_role_skins):
            row = i // items_per_row
            col = i % items_per_row
            x = 80 + col * (item_width + gap)
            y = current_y + row * (item_height + gap)

            # 判断是否已拥有
            if isinstance(skin, str):
                # 未拥有皮肤
                skin_name = skin
                is_owned = False
                skin_quality = 4  # 未拥有统一使用四星框
                skin_icon_url = ""
            else:
                # 已拥有皮肤
                skin_name = skin.skinName
                is_owned = True
                skin_quality = skin.quality
                skin_icon_url = skin.picUrl

            # 使用 get_skin_img 获取皮肤图标
            skin_icon = await get_skin_img("role", skin_name, skin_icon_url)
            if skin_icon:
                target_w, target_h = 348, 824
                orig_w, orig_h = skin_icon.size

                # 计算缩放比例，使缩放后的图片能完全覆盖目标尺寸（cover）
                ratio = max(target_w / orig_w, target_h / orig_h)
                if ratio > 1:  # 只有原图不够大时才缩放，否则保持原尺寸
                    new_w = int(orig_w * ratio)
                    new_h = int(orig_h * ratio)
                    skin_icon = skin_icon.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    orig_w, orig_h = skin_icon.size

                # 此时图片尺寸一定 >= 目标尺寸，从中心裁剪
                left = (orig_w - target_w) // 2
                top = (orig_h - target_h) // 2
                skin_icon = skin_icon.crop((left, top, left + target_w, top + target_h))

                icon_width, icon_height = skin_icon.size
                max_size = 550
                if icon_width > icon_height:
                    new_width = max_size
                    new_height = int(icon_height * max_size / icon_width)
                else:
                    new_height = max_size
                    new_width = int(icon_width * max_size / icon_height)
                skin_icon = skin_icon.resize((new_width, new_height), Image.Resampling.LANCZOS)
                # 居中显示
                icon_x = x + (item_width - new_width) // 2
                icon_y = y + 5
                card_img.paste(skin_icon, (icon_x, icon_y), skin_icon)

            # 绘制皮肤边框
            border_frame = get_skin_border_frame(skin_quality)
            if border_frame:
                # 保持边框原始宽高比缩放
                border_orig_width, border_orig_height = border_frame.size
                max_border_size = 680
                if border_orig_width > border_orig_height:
                    new_border_width = max_border_size
                    new_border_height = int(border_orig_height * max_border_size / border_orig_width)
                else:
                    new_border_height = max_border_size
                    new_border_width = int(border_orig_width * max_border_size / border_orig_height)
                border_frame = border_frame.resize((new_border_width, new_border_height), Image.Resampling.LANCZOS)
                # 居中显示边框
                border_x = x + (item_width - new_border_width) // 2
                border_y = y + (item_height - new_border_height) // 2
                card_img.paste(border_frame, (border_x, border_y), border_frame)

            # 绘制皮肤名称
            name_draw = ImageDraw.Draw(card_img)
            name_draw.text((x + item_width // 2, y + 510), skin_name, "white", waves_font_26, "mm")

            # 绘制拥有状态
            if is_owned:
                name_draw.text((x + item_width // 2, y + 540), "已拥有", (255, 215, 0), waves_font_25, "mm")
            else:
                name_draw.text((x + item_width // 2, y + 540), "未拥有", GREY, waves_font_25, "mm")

        current_y += role_skin_rows * (item_height + gap) + 30

    # 绘制武器皮肤
    if all_weapon_skins:
        draw_section_header(draw, other_left_padding, current_y, "武器皮肤")
        current_y += other_section_height

        for i, skin in enumerate(all_weapon_skins):
            row = i // other_items_per_row
            col = i % other_items_per_row
            x = other_left_padding + col * (other_item_width + other_gap)
            y = current_y + row * (other_item_height + other_gap)

            if isinstance(skin, str):
                skin_name = skin
                is_owned = False
                skin_quality = 4
                skin_icon_url = ""
            else:
                skin_name = skin.skinName
                is_owned = True
                skin_quality = skin.quality
                skin_icon_url = skin.skinIcon

            # 绘制品质边框
            quality_border = get_quality_border(skin_quality)
            if quality_border:
                quality_border = quality_border.resize((other_item_width, other_item_height), Image.Resampling.LANCZOS)
                # 未拥有则边框也绘制灰色
                if not is_owned:
                    quality_border = to_grayscale(quality_border)
                card_img.paste(quality_border, (x, y), quality_border)

            # 使用 get_skin_img 获取皮肤图标
            skin_icon = await get_skin_img("weapon", skin_name, skin_icon_url)
            if skin_icon:
                # 缩放图标适配卡片
                icon_size = 185
                skin_icon = skin_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                # 未拥有则绘制灰色
                if not is_owned:
                    skin_icon = to_grayscale(skin_icon)
                icon_x = x + (other_item_width - icon_size) // 2
                icon_y = y + 17
                card_img.paste(skin_icon, (icon_x, icon_y), skin_icon)

            # 绘制皮肤名称
            name_draw = ImageDraw.Draw(card_img)
            name_draw.text(
                (x + other_item_width // 2, y + other_item_height + 18),
                skin_name,
                "white",
                waves_font_26,
                "mm",
            )

        current_y += weapon_skin_rows * (other_item_height + other_gap) + 20

    # 绘制终端皮肤
    if all_calabash_skins:
        draw_section_header(draw, other_left_padding, current_y, "终端皮肤")
        current_y += other_section_height

        for i, skin in enumerate(all_calabash_skins):
            row = i // other_items_per_row
            col = i % other_items_per_row
            x = other_left_padding + col * (other_item_width + other_gap)
            y = current_y + row * (other_item_height + other_gap)

            if isinstance(skin, str):
                skin_name = skin
                is_owned = False
                skin_quality = 4
                skin_icon_url = ""
            else:
                skin_name = skin.skinName
                is_owned = True
                skin_quality = skin.quality
                skin_icon_url = skin.skinIcon

            # 绘制品质边框
            quality_border = get_quality_border(skin_quality)
            if quality_border:
                quality_border = quality_border.resize((other_item_width, other_item_height), Image.Resampling.LANCZOS)
                # 未拥有则边框也绘制灰色
                if not is_owned:
                    quality_border = to_grayscale(quality_border)
                card_img.paste(quality_border, (x, y), quality_border)

            # 使用 get_skin_img 获取皮肤图标
            skin_icon = await get_skin_img("calabash", skin_name, skin_icon_url)
            if skin_icon:
                # 缩放图标适配卡片
                icon_size = 185
                skin_icon = skin_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                # 未拥有则绘制灰色
                if not is_owned:
                    skin_icon = to_grayscale(skin_icon)
                icon_x = x + (other_item_width - icon_size) // 2
                icon_y = y + 17
                card_img.paste(skin_icon, (icon_x, icon_y), skin_icon)

            # 绘制皮肤名称
            name_draw = ImageDraw.Draw(card_img)
            name_draw.text(
                (x + other_item_width // 2, y + other_item_height + 18),
                skin_name,
                "white",
                waves_font_26,
                "mm",
            )

        current_y += calabash_rows * (other_item_height + other_gap) + 20

    # 绘制翅膀皮肤
    if all_fly_skins:
        draw_section_header(draw, other_left_padding, current_y, "翅膀皮肤")
        current_y += other_section_height

        for i, skin in enumerate(all_fly_skins):
            row = i // other_items_per_row
            col = i % other_items_per_row
            x = other_left_padding + col * (other_item_width + other_gap)
            y = current_y + row * (other_item_height + other_gap)

            if isinstance(skin, str):
                skin_name = skin
                is_owned = False
                skin_quality = 4
                skin_icon_url = ""
            else:
                skin_name = skin.skinName
                is_owned = True
                skin_quality = skin.quality
                skin_icon_url = skin.skinIcon

            # 绘制品质边框
            quality_border = get_quality_border(skin_quality)
            if quality_border:
                quality_border = quality_border.resize((other_item_width, other_item_height), Image.Resampling.LANCZOS)
                # 未拥有则边框也绘制灰色
                if not is_owned:
                    quality_border = to_grayscale(quality_border)
                card_img.paste(quality_border, (x, y), quality_border)

            # 使用 get_skin_img 获取皮肤图标
            skin_icon = await get_skin_img("fly", skin_name, skin_icon_url)
            if skin_icon:
                # 缩放图标适配卡片
                icon_size = 185
                skin_icon = skin_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                # 未拥有则绘制灰色
                if not is_owned:
                    skin_icon = to_grayscale(skin_icon)
                icon_x = x + (other_item_width - icon_size) // 2
                icon_y = y + 17
                card_img.paste(skin_icon, (icon_x, icon_y), skin_icon)

            # 绘制皮肤名称
            name_draw = ImageDraw.Draw(card_img)
            name_draw.text(
                (x + other_item_width // 2, y + other_item_height + 18),
                skin_name,
                "white",
                waves_font_26,
                "mm",
            )

        current_y += equip_rows * (other_item_height + other_gap) + 20

    # 绘制角色装饰
    if all_ornament_skins:
        draw_section_header(draw, other_left_padding, current_y, "角色装饰")
        current_y += other_section_height

        for i, decoration in enumerate(all_ornament_skins):
            row = i // other_items_per_row
            col = i % other_items_per_row
            x = other_left_padding + col * (other_item_width + other_gap)
            y = current_y + row * (other_item_height + other_gap)

            if isinstance(decoration, str):
                deco_name = decoration
                is_owned = False
                deco_quality = 4
                deco_icon_url = ""
            else:
                deco_name = decoration.name
                is_owned = True
                deco_quality = decoration.quality
                deco_icon_url = decoration.icon

            # 绘制品质边框
            quality_border = get_quality_border(deco_quality)
            if quality_border:
                quality_border = quality_border.resize((other_item_width, other_item_height), Image.Resampling.LANCZOS)
                # 未拥有则边框也绘制灰色
                if not is_owned:
                    quality_border = to_grayscale(quality_border)
                card_img.paste(quality_border, (x, y), quality_border)

            # 使用 get_skin_img 获取装饰图标
            deco_icon = await get_skin_img("ornament", deco_name, deco_icon_url)
            if deco_icon:
                # 缩放图标适配卡片
                icon_size = 185
                deco_icon = deco_icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
                # 未拥有则绘制灰色
                if not is_owned:
                    deco_icon = to_grayscale(deco_icon)
                icon_x = x + (other_item_width - icon_size) // 2
                icon_y = y + 17
                card_img.paste(deco_icon, (icon_x, icon_y), deco_icon)

            # 绘制装饰名称
            name_draw = ImageDraw.Draw(card_img)
            name_draw.text(
                (x + other_item_width // 2, y + other_item_height + 18),
                deco_name,
                "white",
                waves_font_26,
                "mm",
            )

    # 添加底部
    card_img = add_footer(card_img, 600, 20)
    card_img = await convert_img(card_img)
    return card_img
