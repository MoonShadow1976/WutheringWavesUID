from pathlib import Path

from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import crop_center_img
from PIL import Image, ImageDraw

from ..utils.api.model import (
    AccountBaseInfo,
    MatrixData,
    RoleDetailData,
    RoleList,
)
from ..utils.char_info_utils import get_all_roleid_detail_info
from ..utils.error_reply import WAVES_CODE_102
from ..utils.fonts.waves_fonts import (
    waves_font_18,
    waves_font_20,
    waves_font_25,
    waves_font_26,
    waves_font_30,
    waves_font_32,
    waves_font_36,
    waves_font_42,
)
from ..utils.hint import error_reply
from ..utils.image import GOLD, GREY, add_footer, pic_download_from_url
from ..utils.imagetool import draw_pic, draw_pic_with_ring
from ..utils.resource.RESOURCE_PATH import MATRIX_PATH
from ..utils.waves_api import waves_api
from ..wutheringwaves_config import PREFIX

TEXT_PATH = Path(__file__).parent / "texture2d"

MATRIX_ERROR_MESSAGE_NO_DATA = "当前暂无终焉矩阵数据\n"
MATRIX_ERROR_MESSAGE_NO_UNLOCK = "终焉矩阵暂未解锁\n"

MATRIX_MODE_NAMES = {
    0: "稳态协议",
    1: "奇点扩张",
}
no_login_msg = [
    "[鸣潮]",
    ">您当前为仅绑定鸣潮特征码",
    f">请使用命令【{PREFIX}登录】后查询详细终焉矩阵数据",
    "",
]
MATRIX_ERROR_MESSAGE_LOGIN = "\n".join(no_login_msg)


async def get_matrix_data(uid: str, ck: str, is_self_ck: bool):
    matrix_data = await waves_api.get_matrix_detail(uid, ck)

    if not matrix_data.success:
        return matrix_data.throw_msg()

    matrix_data = matrix_data.data
    if not matrix_data or (isinstance(matrix_data, dict) and not matrix_data.get("isUnlock", False)):
        if not is_self_ck:
            return MATRIX_ERROR_MESSAGE_LOGIN
        return MATRIX_ERROR_MESSAGE_NO_DATA
    else:
        return MatrixData.model_validate(matrix_data)


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
    if isinstance(matrix_data, str) or not matrix_data:
        return matrix_data
    if not matrix_data.isUnlock:
        return MATRIX_ERROR_MESSAGE_NO_UNLOCK

    if not matrix_data.modeDetails:
        return MATRIX_ERROR_MESSAGE_NO_DATA

    # 先创建一个足够大的画布，使用矩阵专属背景
    matrix_bg_original = Image.open(TEXT_PATH / "matrix_bg.png").convert("RGBA")
    # 使用crop_center_img裁剪中心区域，不拉伸图片
    card_img = crop_center_img(matrix_bg_original, 950, 5000)

    # 基础信息 名字 特征码
    base_info_bg = Image.open(TEXT_PATH / "base_info_bg.png")
    base_info_draw = ImageDraw.Draw(base_info_bg)
    base_info_draw.text((275, 120), f"{account_info.name[:7]}", "white", waves_font_30, "lm")
    base_info_draw.text((226, 173), f"特征码:  {account_info.id}", GOLD, waves_font_25, "lm")
    card_img.paste(base_info_bg, (15, 20), base_info_bg)

    # 头像 头像环
    avatar, avatar_ring = await draw_pic_with_ring(ev)
    card_img.paste(avatar, (25, 70), avatar)
    card_img.paste(avatar_ring, (35, 80), avatar_ring)

    # 账号基本信息
    if account_info.is_full:
        title_bar = Image.open(TEXT_PATH / "title_bar.png")
        title_bar_draw = ImageDraw.Draw(title_bar)
        title_bar_draw.text((660, 125), "账号等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((660, 78), f"Lv.{account_info.level}", "white", waves_font_42, "mm")

        title_bar_draw.text((810, 125), "世界等级", GREY, waves_font_26, "mm")
        title_bar_draw.text((810, 78), f"Lv.{account_info.worldLevel}", "white", waves_font_42, "mm")
        card_img.paste(title_bar, (-20, 70), title_bar)

    # 根据面板数据获取详细信息
    role_detail_info_map = await get_all_roleid_detail_info(uid)

    # 从这里开始绘制模式数据
    y_offset = 330

    # 绘制每个模式的数据
    for mode_index, mode in enumerate(matrix_data.modeDetails):
        if not mode.hasRecord:
            continue

        # 模式信息背景
        mode_bg = Image.new("RGBA", (900, 100), (0, 0, 0, 0))
        mode_draw = ImageDraw.Draw(mode_bg)
        mode_draw.rounded_rectangle([(0, 0), (900, 100)], radius=10, fill=(40, 40, 60, 180))

        mode_name = MATRIX_MODE_NAMES.get(mode.modeId, f"模式 {mode.modeId}")
        # 主标题上下居中
        mode_draw.text((30, 50), mode_name, "white", waves_font_32, "lm")

        # 显示评级图标（根据分数自动选择）
        score = mode.score

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
                rank_icon_name = "matrix_largerempty.png"
                score_color = GREY  # 未达标 - 灰色
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
            else:
                rank_icon_name = "matrix_largerempty.png"
                score_color = GREY  # 未达标 - 灰色

        if rank_icon_name:
            try:
                rank_icon = Image.open(TEXT_PATH / rank_icon_name)
                rank_icon = rank_icon.resize((80, 80), Image.Resampling.LANCZOS)
                mode_bg.paste(rank_icon, (640, 10), rank_icon)
            except Exception:
                pass

        # 在评级图标后面显示总分数（大号字体，上下居中，增加间隔，根据等级显示不同颜色）
        mode_draw.text((800, 47), f"{mode.score}", score_color, waves_font_42, "mm")

        card_img.paste(mode_bg, (25, y_offset), mode_bg)
        y_offset += 120

        # 绘制队伍信息
        if mode.teams:
            for team_index, team in enumerate(mode.teams):
                team_bg = Image.new("RGBA", (900, 200), (0, 0, 0, 0))
                team_draw = ImageDraw.Draw(team_bg)
                team_draw.rounded_rectangle([(0, 0), (900, 200)], radius=10, fill=(30, 30, 50, 150))

                team_draw.text((20, 20), f"第{team.round}轮", "white", waves_font_26, "lm")
                team_draw.text((20, 50), f"通关: {team.passBoss}/{team.bossCount}", GREY, waves_font_20, "lm")
                # 显示分数图标（在分数前面）
                try:
                    score_icon = Image.open(TEXT_PATH / "matrix_score.png")
                    score_icon = score_icon.resize((50, 50), Image.Resampling.LANCZOS)
                    team_bg.paste(score_icon, (20, 70), score_icon)
                except Exception:
                    pass

                # 分数显示在图标后面
                team_draw.text((80, 93), f"{team.score}", GOLD, waves_font_36, "lm")

                # 绘制增益信息和图标（在分数下方）
                if team.buffs and len(team.buffs) > 0:
                    buff = team.buffs[0]
                    buff_text = buff.buffName[:10]

                    # 下载并显示增益图标（在文本前面）
                    if buff.buffIcon:
                        try:
                            buff_pic = await pic_download_from_url(MATRIX_PATH, buff.buffIcon)
                            buff_pic = buff_pic.resize((40, 40))
                            team_bg.paste(buff_pic, (20, 135), buff_pic)
                            # 图标后面显示文字
                            team_draw.text((70, 155), f"增益: {buff_text}", "white", waves_font_20, "lm")
                        except Exception:
                            # 如果图标加载失败，只显示文字
                            team_draw.text((20, 155), f"增益: {buff_text}", "white", waves_font_20, "lm")
                    else:
                        team_draw.text((20, 155), f"增益: {buff_text}", "white", waves_font_20, "lm")

                # 绘制角色头像
                if team.roleIcons and len(team.roleIcons) > 0:
                    for role_index, icon_url in enumerate(team.roleIcons[:3]):
                        if not icon_url:
                            continue

                        # 通过roleIconUrl匹配找到对应的角色
                        role = next(
                            (r for r in role_info.roleList if r.roleIconUrl == icon_url),
                            None,
                        )
                        if not role:
                            continue

                        # 使用draw_pic获取角色头像（与深塔海墟一致）
                        avatar = await draw_pic(role.roleId)
                        char_bg = Image.open(TEXT_PATH / f"char_bg{role.starLevel}.png")
                        char_bg_draw = ImageDraw.Draw(char_bg)
                        char_bg_draw.text((90, 150), f"{role.roleName}", "white", waves_font_18, "mm")
                        char_bg.paste(avatar, (0, 0), avatar)

                        if role_detail_info_map and str(role.roleId) in role_detail_info_map:
                            temp: RoleDetailData = role_detail_info_map[str(role.roleId)]
                            info_block = Image.new("RGBA", (40, 20), color=(255, 255, 255, 0))
                            info_block_draw = ImageDraw.Draw(info_block)
                            info_block_draw.rectangle([0, 0, 40, 20], fill=(96, 12, 120, int(0.9 * 255)))
                            info_block_draw.text(
                                (2, 10),
                                f"{temp.get_chain_name()}",
                                "white",
                                waves_font_18,
                                "lm",
                            )
                            char_bg.paste(info_block, (110, 35), info_block)

                        team_bg.alpha_composite(char_bg, (350 + role_index * 150, 0))
                else:
                    # 当没有角色信息时显示提示（在三个角色头像中间位置，上下居中）
                    team_draw.text((575, 100), "暂无角色数据", GREY, waves_font_20, "mm")

                card_img.paste(team_bg, (25, y_offset), team_bg)
                y_offset += 220

    # 上传矩阵数据到排行榜
    await upload_matrix_record(is_self_ck, uid, matrix_data, role_info, role_detail_info_map)

    # 裁剪画布到实际使用的高度，添加适当的底部边距
    final_height = y_offset + 50  # 添加50px底部边距
    card_img = card_img.crop((0, 0, 950, final_height))

    card_img = add_footer(card_img, 600, 20)
    card_img = await convert_img(card_img)
    return card_img


async def upload_matrix_record(
    is_self_ck: bool,
    waves_id: str,
    matrix_data: MatrixData,
    role_info: RoleList,
    role_detail_info_map: dict,
):
    """上传矩阵数据到排行榜服务器"""
    from gsuid_core.logger import logger

    from ..utils.queues.const import QUEUE_MATRIX_RECORD
    from ..utils.queues.queues import push_item
    from ..wutheringwaves_config import WutheringWavesConfig

    WavesToken = WutheringWavesConfig.get_config("WavesToken").data
    if not WavesToken:
        logger.info("[矩阵数据上传] 跳过上传: 未配置WavesToken")
        return

    if not matrix_data:
        logger.info("[矩阵数据上传] 跳过上传: 矩阵数据为空")
        return
    if not matrix_data.modeDetails:
        logger.info("[矩阵数据上传] 跳过上传: 无模式数据")
        return
    if not is_self_ck:
        logger.info("[矩阵数据上传] 跳过上传: 非自己的CK")
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
        role_detail = role_detail_info_map.get(str(role.roleId))
        chain = role_detail.get_chain_num() if role_detail else 0

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
    from gsuid_core.logger import logger

    logger.info(
        f"[矩阵数据上传] 特征码: {waves_id}, 总分: {singularity_mode.score}, 队伍分数: {highest_team.score}, 角色数: {len(char_infos)}, 队伍数量: {len(singularity_mode.teams)}"
    )
    push_item(QUEUE_MATRIX_RECORD, matrix_item)
