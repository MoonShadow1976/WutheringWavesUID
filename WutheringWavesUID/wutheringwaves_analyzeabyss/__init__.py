"""slash/abyss/matrix 挑战分享图上传命令层.

3 种挑战 key 与 abyss 模块/wwapi 对齐:
  slash (海墟/无尽/禁忌/湍渊/冥海)  - 已实现
  abyss (深塔)  - 已实现 (识别+星级+入库+绘图)
  matrix (矩阵) - 预留
"""

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..utils.at_help import ruser_id
from ..utils.database.models import WavesBind
from ..utils.error_reply import WAVES_CODE_103
from ..utils.hint import error_reply
from .abyss_data_utils import (
    IMPLEMENTED_TYPES,
    TYPE_ABYSS,
    TYPE_MATRIX,
    TYPE_SLASH,
    ctype_label,
    set_challenge_data,
)
from .slash_processor import run_full_slash_recognize
from .toa_processor import run_toa_recognize

sv_waves_upload_haixu = SV("waves上传海墟分享图", priority=4)
sv_waves_upload_abyss = SV("waves上传深塔分享图", priority=4)
sv_waves_upload_matrix = SV("waves上传矩阵分享图", priority=4)

_NOT_IMPL = "[鸣潮]上传{}：敬请期待，暂未开放~\n目前已开放：上传海墟（包含 无尽/禁忌/冥歌海墟/湍渊）。\n"


async def _get_imgs(ev: Event):
    from ..wutheringwaves_analyzecard.ocrspace import get_upload_img

    return await get_upload_img(ev)


def _at(ev: Event) -> bool:
    return bool(ev.group_id)


async def _process_slash_image(bot: Bot, ev: Event, imgs):
    at = _at(ev)
    if not imgs:
        return await bot.send(f"[鸣潮]获取{ctype_label(TYPE_SLASH)}分享图失败，请重新发命令并发图。\n", at)
    img = imgs[0]
    r, _share = await run_full_slash_recognize(bot, ev.user_id, at, img)
    if r.summary_lines and r.summary_lines[0].startswith("[OCR_ERROR]"):
        return await bot.send(r.summary_lines[0].replace("[OCR_ERROR]", "", 1), at)
    if r.match_empty:
        return await bot.send("[鸣潮]未能识别到任何角色与信物，请确认分享图完整清晰。\n", at)
    user_id = ruser_id(ev)
    bound_uid = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    save_uid = r.recognized_uid or (str(bound_uid) if bound_uid else None)
    uid_warn = ""
    if r.recognized_uid and bound_uid and str(r.recognized_uid) != str(bound_uid):
        uid_warn = f"⚠ 识别到分享图特征码 {r.recognized_uid}，与您绑定的 {bound_uid} 不一致，将按图中特征码写入~\n"
    if not save_uid:
        return await bot.send(
            error_reply(WAVES_CODE_103) + "（若分享图未识别到特征码，请先在机器人处绑定特征码再重试）\n",
            at,
        )
    header = f"{uid_warn}[鸣潮]{ctype_label(TYPE_SLASH)}分享图识别成功！写入特征码: {save_uid}\n"
    logger.info(header + "\n".join(r.summary_lines) + "\n正在绘制卡片，请稍候…\n")
    ok = await set_challenge_data(save_uid, TYPE_SLASH, r.slash_dict or {})
    if not ok:
        await bot.send(f"[鸣潮]警告: 保存{ctype_label(TYPE_SLASH)}数据失败，仍尝试绘制～\n", at)
    from ..wutheringwaves_abyss.draw_slash_card import draw_slash_img

    result = await draw_slash_img(ev, str(save_uid), user_id)
    if isinstance(result, str):
        return await bot.send(result, at)
    return await bot.send(result)


async def _process_toa_image(bot: Bot, ev: Event, imgs):
    at = _at(ev)
    if not imgs:
        return await bot.send(f"[鸣潮]获取{ctype_label(TYPE_ABYSS)}分享图失败，请重新发命令并发图。\n", at)
    img = imgs[0]
    user_id = ruser_id(ev)
    bound_uid = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    save_uid = str(bound_uid) if bound_uid else None
    if not save_uid:
        return await bot.send(
            error_reply(WAVES_CODE_103) + "（请先在机器人处绑定特征码再重试）\n",
            at,
        )
    logger.info(f"[鸣潮][上传{ctype_label(TYPE_ABYSS)}] 开始识别, 特征码: {save_uid}")
    result = await run_toa_recognize(bot, ev, img, save_uid, user_id)
    if isinstance(result, str):
        return await bot.send(result, at)
    return await bot.send(result)


async def _upload_entry(bot: Bot, ev: Event, ctype: str):
    at = _at(ev)
    if ctype not in IMPLEMENTED_TYPES:
        return await bot.send(_NOT_IMPL.format(ctype_label(ctype)), at)
    ok, imgs = await _get_imgs(ev)
    processor = _process_toa_image if ctype == TYPE_ABYSS else _process_slash_image
    if ok and imgs:
        return await processor(bot, ev, imgs)
    hint = (
        f"[鸣潮][上传{ctype_label(ctype)}] 请在30秒内发送一张{ctype_label(ctype)}分享截图。\n"
        "参考分辨率约 1747×983，过低可能导致识别失败。\n"
    )
    await bot.send(hint, at)
    resp = await bot.receive_resp(timeout=30)
    if resp is None:
        return await bot.send(f"[鸣潮]等待超时，上传{ctype_label(ctype)}已关闭。\n", at)
    ok2, imgs2 = await _get_imgs(resp)
    if not ok2 or not imgs2:
        return await bot.send(
            f"[鸣潮]未检测到图片，请重新使用「上传{ctype_label(ctype)}」命令并发送图片。\n",
            at,
        )
    await processor(bot, ev, imgs2)


@sv_waves_upload_haixu.on_command(
    (
        "上传海墟",
        "海墟上传",
        "上传无尽",
        "无尽上传",
        "上传无尽深渊",
        "上传禁忌",
        "禁忌上传",
        "上传冥海",
        "冥海上传",
        "上传冥歌海墟",
        "上传湍渊",
        "湍渊上传",
    ),
    block=True,
)
async def upload_haixu_cmd(bot: Bot, ev: Event) -> None:
    logger.info("[鸣潮][上传海墟] 开始处理")
    await _upload_entry(bot, ev, TYPE_SLASH)


@sv_waves_upload_abyss.on_command(
    ("上传深塔", "深塔上传", "上传高塔", "高塔上传", "上传深渊", "深渊上传"),
    block=True,
)
async def upload_abyss_cmd(bot: Bot, ev: Event) -> None:
    logger.info("[鸣潮][上传深塔] 开始处理")
    await _upload_entry(bot, ev, TYPE_ABYSS)


@sv_waves_upload_matrix.on_command(
    ("上传矩阵", "矩阵上传", "上传矩阵战略", "矩阵战略上传", "上传终焉矩阵", "终焉矩阵上传"),
    block=True,
)
async def upload_matrix_cmd(bot: Bot, ev: Event) -> None:
    logger.info("[鸣潮][上传矩阵] 触发 (预留, 暂未开放)")
    await _upload_entry(bot, ev, TYPE_MATRIX)
