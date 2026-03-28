from pathlib import Path

from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw

from ..utils.api.model import (
    AccountBaseInfo,
    MatrixData,
    RoleList,
)
from ..utils.char_info_utils import get_all_roleid_detail_info
from ..utils.error_reply import WAVES_CODE_102
from ..utils.fonts.waves_fonts import (
    waves_font_16,
    waves_font_20,
    waves_font_25,
    waves_font_26,
    waves_font_30,
    waves_font_42,
)
from ..utils.hint import error_reply
from ..utils.image import GOLD, GREY, add_footer, get_random_share_bg, pic_download_from_url
from ..utils.imagetool import draw_pic_with_ring, get_square_avatar
from ..utils.queues.const import QUEUE_MATRIX_RECORD
from ..utils.queues.queues import push_item
from ..utils.resource.RESOURCE_PATH import MATRIX_PATH
from ..utils.waves_api import waves_api
from ..wutheringwaves_config import WutheringWavesConfig

TEXT_PATH = Path(__file__).parent / "texture2d"

MATRIX_ERROR_MESSAGE_NO_DATA = "当前暂无终焉矩阵数据\n"
MATRIX_ERROR_MESSAGE_NO_UNLOCK = "终焉矩阵暂未解锁\n"

MATRIX_MODE_NAMES = {
    0: "稳态协议",
    1: "奇点扩张",
}


async def get_matrix_data(uid: str, ck: str, is_self_ck: bool):
    if is_self_ck:
        matrix_data = await waves_api.get_matrix_detail(uid, ck)
    else:
        matrix_data = await waves_api.get_matrix_index(uid, ck)

    if not matrix_data.success:
        return matrix_data.throw_msg()

    matrix_data = matrix_data.data
    if not matrix_data:
        if not is_self_ck:
            return MATRIX_ERROR_MESSAGE_NO_UNLOCK
        return MATRIX_ERROR_MESSAGE_NO_DATA

    matrix_data = MatrixData.model_validate(matrix_data)

    if not matrix_data.isUnlock:
        return MATRIX_ERROR_MESSAGE_NO_UNLOCK
    if not matrix_data.modeDetails:
        return MATRIX_ERROR_MESSAGE_NO_DATA

    return matrix_data


async def draw_matrix_img(ev: Event, uid: str, user_id: str) -> bytes | str:
    is_self_ck, ck = await waves_api.get_ck_result(uid, user_id, ev.bot_id)
    if not ck:
        return error_reply(WAVES_CODE_102)

    # 账户数据
    account_info = await waves_api.get_base_info(uid, ck)
    if not account_info.success:
        return account_info.throw_msg()
    account_info = AccountBaseInfo.model_validate(account_info.data)

    # 共鸣者信息
    role_info = await waves_api.get_role_info(uid, ck)
    if not role_info.success:
        return role_info.throw_msg()

    role_info = RoleList.model_validate(role_info.data)

    # 终焉矩阵
    matrix_data = await get_matrix_data(uid, ck, is_self_ck)
    if isinstance(matrix_data, str):
        return matrix_data

    command = ev.command
    text = ev.text.strip()
    modeIds = [1] if is_self_ck else [1, 0]  # MATRIX_MODE_NAMES
    if "稳态" in text or "稳态" in command:
        modeIds = [0]
    elif text.isdigit() and 0 <= int(text) <= 1:
        modeIds = [int(text)]
    logger.debug(f"[鸣潮][终焉矩阵] modeIds: {modeIds}")

    # 画布 2560 * 1440
    card_img = await get_random_share_bg()  # 已返回 2560 x 1440 图像
    img = Image.new("RGBA", (2560, 1440), (30, 45, 65, 70))  # 遮罩
    card_img = Image.alpha_composite(card_img, img)

    # 基础信息
    base_info_bg = Image.new("RGBA", (2560, 1440), (0, 0, 0, 0))
    base_info = Image.open(TEXT_PATH / "base_info_bg.png")
    base_info_draw = ImageDraw.Draw(base_info)
    base_info_draw.text((275, 120), f"{account_info.name[:7]}", "white", waves_font_30, "lm")
    base_info_draw.text((226, 173), f"特征码:  {account_info.id}", GOLD, waves_font_25, "lm")
    base_info_bg.paste(base_info, (-30, -70), base_info)

    # 头像、头像环
    avatar, avatar_ring = await draw_pic_with_ring(ev)
    base_info_bg.paste(avatar, (-20, -20), avatar)
    base_info_bg.paste(avatar_ring, (-10, -10), avatar_ring)

    # 账号基本信息
    if account_info.is_full:
        title_bar = Image.open(TEXT_PATH / "title_bar.png")
        title_bar_draw = ImageDraw.Draw(title_bar)
        title_bar_draw.text((660, 125), "账号等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((660, 78), f"Lv.{account_info.level}", "white", waves_font_42, "mm")
        title_bar_draw.text((810, 125), "世界等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((810, 78), f"Lv.{account_info.worldLevel}", "white", waves_font_42, "mm")
        base_info_bg.paste(title_bar, (-65, -20), title_bar)

    base_info_bg = base_info_bg.resize((int(2560 * 0.8), int(1440 * 0.8)))
    card_img.paste(base_info_bg, (30, 10), base_info_bg)

    # 获取角色详情
    role_detail_info_map = await get_all_roleid_detail_info(uid)

    # 绘制模式数据（改用内容宽度 1220，左右边距 30）
    y_offset = 200
    content_width = 1500 - 60  # 左右边距各30
    available_height = card_img.height - y_offset - 100  # 1275 - 100 底部留空

    # 卡片基础尺寸与比例（宽128，高448，比例 1:3.5）
    base_width = 128
    team_header_height = 76
    team_role_height = 124
    base_height = team_role_height * 3 + team_header_height  # 三角色 一标题
    aspect_ratio = base_height / base_width  # 3.5

    # 间距
    card_h_gap = 20  # 水平间距
    card_v_gap = 40  # 垂直间距

    for mode_index, mode in enumerate(matrix_data.modeDetails):
        if not mode.hasRecord:
            continue
        if mode.modeId not in modeIds:
            continue

        # 模式信息背景（宽度自适应）
        mode_bg = Image.open(TEXT_PATH / "matrix_score_level_bg.png")
        mode_bg = mode_bg.resize((528, 360), Image.Resampling.LANCZOS)
        mode_draw = ImageDraw.Draw(mode_bg)

        # 评级与分数（位置根据新宽度微调）
        score = mode.score
        rank_icon_name = "matrix_largerempty.png"
        score_color = GREY  # 未达标 - 灰色

        # 稳态协议（modeId=0）使用不同的评分标准
        if mode.modeId == 0:
            if score >= 10000:
                rank_icon_name = "matrix_s.png"
                score_color = "#FFA500"  # S - 浅橙色
            elif score >= 7200:
                rank_icon_name = "matrix_a.png"
                score_color = "#FFB84D"  # A - 浅金色
            elif score >= 4800:
                rank_icon_name = "matrix_b.png"
                score_color = "#FFCC66"  # B - 淡金色
        else:
            # 奇点扩张（modeId=1）使用原有的评分标准
            if score >= 58000:
                rank_icon_name = "matrix_largerkingcolor.png"
                score_color = "#FF00FF"  # 彩色王者 - 紫红色
            elif score >= 45000:
                rank_icon_name = "matrix_largerkinggold.png"
                score_color = "#FFD700"  # 金色王者 - 金色
            elif score >= 37000:
                rank_icon_name = "matrix_sss.png"
                score_color = "#FF6B00"  # SSS - 橙红色
            elif score >= 29000:
                rank_icon_name = "matrix_ss.png"
                score_color = "#FF8C00"  # SS - 橙色
            elif score >= 21000:
                rank_icon_name = "matrix_s.png"
                score_color = "#FFA500"  # S - 浅橙色
            elif score >= 16000:
                rank_icon_name = "matrix_a.png"
                score_color = "#FFB84D"  # A - 浅金色
            elif score >= 12000:
                rank_icon_name = "matrix_b.png"
                score_color = "#FFCC66"  # B - 淡金色

        if rank_icon_name:
            try:
                rank_icon = Image.open(TEXT_PATH / rank_icon_name)
                rank_icon = rank_icon.resize((320, 320), Image.Resampling.LANCZOS)
                mode_bg.paste(
                    rank_icon, ((mode_bg.width - rank_icon.width) // 2, (mode_bg.height - rank_icon.height) // 2), rank_icon
                )
            except Exception:
                pass

        # 分数显示在图右侧
        mode_draw.text((mode_bg.width // 2, mode_bg.height - 40), f"{mode.score}", score_color, waves_font_42, "mm")

        fix_y = 100
        if len(modeIds) > 1 and mode_index > 0 and not mode.teams:
            fix_y = -360
            bug_draw = ImageDraw.Draw(card_img)
            bug_draw.text((100, 400), "请登录查询完整数据", GREY, waves_font_42, "lm")

        card_img.paste(mode_bg, (2560 - mode_bg.width, y_offset - fix_y), mode_bg)

        if mode.teams:
            team_count = len(mode.teams)

            # 寻找最优每行数量 N 和缩放因子 factor
            if team_count < 5:  # 避免队伍卡片过大
                available_height = available_height // 5 * 3
            best_N = 1
            best_factor = 0.0
            for N in range(1, team_count + 1):
                # 水平最小宽度
                min_width = N * base_width + (N - 1) * card_h_gap
                if min_width > content_width:
                    continue
                # 水平方向最大宽度（填满）
                max_width_by_width = (content_width - (N - 1) * card_h_gap) / N
                # 所需行数
                rows = (team_count + N - 1) // N
                # 垂直方向允许的最大高度
                max_height_per_card = (available_height - (rows - 1) * card_v_gap) / rows
                max_width_by_height = max_height_per_card / aspect_ratio
                # 实际宽度取较小值，得到缩放因子
                actual_width = min(max_width_by_width, max_width_by_height)
                factor = actual_width / base_width
                if factor > best_factor:
                    best_factor = factor
                    best_N = N

            # 若未找到（如队伍太多，水平放不下），则取最小宽度并限制高度
            if best_factor <= 0:
                best_N = max(1, int(content_width / (base_width + card_h_gap)))
                best_factor = min(1.0, (content_width - (best_N - 1) * card_h_gap) / (best_N * base_width))
                rows = (team_count + best_N - 1) // best_N
                max_height_per_card = (available_height - (rows - 1) * card_v_gap) / rows
                max_factor_by_height = max_height_per_card / base_height
                best_factor = min(best_factor, max_factor_by_height)

            # 最终卡片尺寸
            card_width = int(base_width * best_factor)
            card_height = int(base_height * best_factor)
            logger.debug(f"最终尺寸：{card_width}x{card_height}, 缩放因子：{best_factor}, 一行队伍数：{best_N}")

            # 加载并缩放装饰背景到原始尺寸
            team_card_line_deco = Image.open(TEXT_PATH / "matrix_team_top.png")
            team_card_line_deco = team_card_line_deco.rotate(180)
            team_card_line_deco = team_card_line_deco.resize((base_width, team_header_height), Image.Resampling.LANCZOS)

            role_card_bg = Image.open(TEXT_PATH / "matrix_role_card_bg.png")
            role_card_bg = role_card_bg.resize((base_width, team_role_height), Image.Resampling.LANCZOS)

            rows = (team_count + best_N - 1) // best_N
            total_teams_height = rows * card_height + (rows - 1) * card_v_gap
            row_y = y_offset

            # 遍历队伍，构建每个队伍的完整卡片（标题区+角色卡）
            for idx, team in enumerate(mode.teams):
                col = idx % best_N
                row = idx // best_N
                x = 30 + col * (card_width + card_h_gap)
                y = row_y + row * (card_height + card_v_gap)

                # 标题区 team_bg
                team_bg = team_card_line_deco.copy()
                team_draw = ImageDraw.Draw(team_bg)

                # 轮次、通关信息、分数
                team_draw.text((10, 65), f"第{team.round}轮 M{team.passBoss}/{team.bossCount}", "white", waves_font_20, "lm")
                team_draw.text((25, 40), f"+{team.score}", GOLD, waves_font_20, "lm")

                # 增益信息
                if team.buffs and len(team.buffs) > 0:
                    buff = team.buffs[0]
                    buff_text = buff.buffName[:4]
                    if buff.buffIcon:
                        try:
                            buff_pic = await pic_download_from_url(MATRIX_PATH, buff.buffIcon)
                            buff_pic = buff_pic.resize((30, 30), Image.Resampling.LANCZOS)
                            team_bg.paste(buff_pic, ((base_width - 30) // 2, 0), buff_pic)
                        except Exception:
                            pass
                    else:
                        team_draw.text((35, 0), f"{buff_text}", "white", waves_font_16, "lm")

                # 构建角色卡列表 role_cards
                role_cards = []
                if team.roleIcons and len(team.roleIcons) > 0:
                    for role_index, icon_url in enumerate(team.roleIcons[:3]):
                        if not icon_url:
                            continue
                        role = next((r for r in role_info.roleList if r.roleIconUrl == icon_url), None)
                        if not role:
                            continue
                        avatar = await get_square_avatar(role.roleId)
                        avatar = avatar.resize((128, 124), Image.Resampling.LANCZOS)
                        role_bg = role_card_bg.copy()
                        role_bg.paste(avatar, (0, 10), avatar)  # 原始偏移 10px
                        role_bg_draw = ImageDraw.Draw(role_bg)
                        role_bg_draw.text((0, 116), f"{role.roleName}", "white", waves_font_16, "lm")  # 居中偏下
                        # 共鸣链信息
                        if role_detail_info_map and str(role.roleId) in role_detail_info_map:
                            temp = role_detail_info_map[str(role.roleId)]
                            info_block = Image.new("RGBA", (35, 17), (0, 0, 0, 0))
                            info_block_draw = ImageDraw.Draw(info_block)
                            info_block_draw.rectangle([0, 0, 35, 17], fill=(96, 12, 120, int(0.9 * 255)))
                            info_block_draw.text((2, 8), f"{temp.get_chain_name()}", "white", waves_font_16, "lm")
                            role_bg.paste(info_block, (82, 10), info_block)
                        role_bg = role_bg.resize((110, 110), Image.Resampling.LANCZOS)
                        role_cards.append(role_bg)

                # 组合标题区 + 角色卡列表
                team_card = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
                team_card_draw = ImageDraw.Draw(team_card)
                team_card_draw.rounded_rectangle([0, 0, base_width, base_height], 50, (30, 30, 50, 150))
                team_card.paste(team_bg, ((base_width - team_bg.width) // 2, 0), team_bg)
                y_offset_role = team_bg.height
                for role_card in role_cards:
                    team_card.paste(role_card, ((base_width - role_card.width) // 2, y_offset_role), role_card)  # 左对齐
                    y_offset_role += role_card.height

                # 将 team_card 粘贴到最终画布
                # 目标尺寸（基于 best_factor 计算）
                card_width = int(128 * best_factor)
                card_height_new = int(team_card.height * best_factor)  # 按实际原始高度等比缩放

                team_card_scaled = team_card.resize((card_width, card_height_new), Image.Resampling.LANCZOS)

                # 粘贴位置仍用原布局的 x,y（布局计算中仍使用 card_height = 448 * best_factor 占位）
                card_img.paste(team_card_scaled, (x, y), team_card_scaled)

            # 更新 y_offset（所有队伍卡片之后）
            y_offset += total_teams_height

    # 上传矩阵数据到排行榜
    await upload_matrix_record(uid, matrix_data, role_info, role_detail_info_map)

    # 裁剪画布到实际使用的高度，并添加页脚
    final_height = max(y_offset, 1440)
    card_img = card_img.crop((0, 0, 2560, final_height))
    card_img = add_footer(card_img, 600, 20, color="black")
    card_img = await convert_img(card_img)
    return card_img


async def upload_matrix_record(
    waves_id: str,
    matrix_data: MatrixData,
    role_info: RoleList,
    role_detail_info_map: dict | None = None,
):
    """上传矩阵数据到排行榜服务器"""
    WavesToken = WutheringWavesConfig.get_config("WavesToken").data
    if not WavesToken:
        logger.info("[矩阵数据上传] 跳过上传: 未配置WavesToken")
        return

    if not matrix_data.modeDetails:
        logger.info("[矩阵数据上传] 跳过上传: 无模式数据")
        return

    # 找到奇点扩张模式（modeId=1）
    singularity_mode = next(
        (mode for mode in matrix_data.modeDetails if mode.modeId == 1),
        None,
    )
    if not singularity_mode:
        logger.info("[矩阵数据上传] 跳过上传: 未找到奇点扩张模式")
        return

    if not singularity_mode.hasRecord:
        logger.info("[矩阵数据上传] 跳过上传: 奇点扩张无记录")
        return

    if not singularity_mode.teams:
        logger.info("[矩阵数据上传] 跳过上传: 奇点扩张无队伍数据")
        return

    # 找到分数最高的队伍
    highest_team = max(singularity_mode.teams, key=lambda t: t.score)

    # 从roleIcons匹配角色（与绘制卡片逻辑一致）
    if not highest_team.roleIcons:
        logger.info("[矩阵数据上传] 跳过上传: 最高分队伍无角色图标")
        return

    # 构建角色信息列表（包含链度）
    char_infos = []
    for icon_url in highest_team.roleIcons:
        # 通过roleIconUrl匹配找到对应的角色（与绘制卡片相同的逻辑）
        role = next(
            (r for r in role_info.roleList if r.roleIconUrl == icon_url),
            None,
        )
        if not role:
            continue

        # 从角色详细信息中获取链度
        chain = None
        if role_detail_info_map:
            role_detail = role_detail_info_map.get(str(role.roleId))
            chain = role_detail.get_chain_num() if role_detail else None

        if chain is None:
            logger.warning(f"[矩阵数据上传] 跳过上传: 无法匹配本地角色信息 (id={role.roleId}, name={role.roleName})")
            return

        char_infos.append(
            {
                "charId": role.roleId,
                "chain": chain,
            }
        )

    if not char_infos:
        logger.info(f"[矩阵数据上传] 跳过上传: 无法匹配角色信息 (roleIcons数量={len(highest_team.roleIcons)})")
        return

    # 获取增益图标
    buff_icon = ""
    if highest_team.buffs and len(highest_team.buffs) > 0:
        buff_icon = highest_team.buffs[0].buffIcon

    # 构建上传数据
    matrix_item = {
        "wavesId": waves_id,
        "team": {
            "charInfos": char_infos,
            "score": highest_team.score,
            "buffIcon": buff_icon,
        },
        "totalScore": singularity_mode.score,
        "teamCount": len(singularity_mode.teams),  # 奇点扩张中的队伍总数量
    }

    # 推送到上传队列
    logger.info(
        f"[矩阵数据上传] 特征码: {waves_id}, 总分: {singularity_mode.score}, 队伍分数: {highest_team.score}, 角色数: {len(char_infos)}, 队伍数量: {len(singularity_mode.teams)}"
    )
    push_item(QUEUE_MATRIX_RECORD, matrix_item)
