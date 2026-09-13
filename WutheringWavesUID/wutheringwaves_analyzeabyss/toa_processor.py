"""深塔 (ToA) 分享图处理.

识别角色 + 星级 + UID, 保存到本地 abyssData.json, 然后绘图。
"""

from dataclasses import dataclass, field
from datetime import datetime

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from PIL import Image

from ..wutheringwaves_analyzecard.ocrspace import ocrspace
from ..wutheringwaves_analyzecard.ScoreQuery import can_score_query_card, set_cache_score_query_card
from .abyss_data_utils import build_abyss_detail_model, save_abyss_detail
from .slash_processor import _parse_uid
from .toa_match import ToaMatchResult, init, read_toa_image


@dataclass
class ToaRecognizeResult:
    match_empty: bool = True
    summary_lines: list[str] = field(default_factory=list)
    tower_role_matrix: list[list[int]] = field(default_factory=list)
    star_counts: list[int] = field(default_factory=list)
    recognized_uid: str | None = None


def _make_summary(r: ToaRecognizeResult) -> list[str]:
    lines = ["深塔分享图识别结果:"]
    tower_names = ["残响之塔", "深境之塔", "回音之塔"]
    # row0->塔1 4层, row1->塔3 4层, row2-5->塔2 1-4层
    mapping = [
        (0, tower_names[0], 4),
        (2, tower_names[1], 1),
        (3, tower_names[1], 2),
        (4, tower_names[1], 3),
        (5, tower_names[1], 4),
        (1, tower_names[2], 4),
    ]
    for row_idx, tname, floor in mapping:
        if row_idx >= len(r.tower_role_matrix):
            continue
        ids = r.tower_role_matrix[row_idx]
        star = r.star_counts[row_idx] if row_idx < len(r.star_counts) else 0
        names = [str(i) for i in ids if i and i > 0]
        lines.append(f"  {tname} 第{floor}层 {'★' * star}{'☆' * (3 - star)}: [{', '.join(names) if names else '无'}]")
    return lines


async def run_toa_recognize(bot: Bot, ev, src: Image.Image, uid: str, user_id: str) -> bytes | str:
    # 时限: 防止同一用户重复触发 OCR
    wait = can_score_query_card(user_id)
    if wait > 0:
        return f"[鸣潮]深塔识别进行中，请等待{wait}秒后再试。\n"
    set_cache_score_query_card(user_id, True)
    try:
        return await _run_toa_recognize(bot, ev, src, uid, user_id)
    finally:
        set_cache_score_query_card(user_id, False)


async def _run_toa_recognize(bot, ev, src, uid, user_id) -> bytes | str:
    try:
        init()
    except Exception as e:
        logger.warning(f"[ww-toa-processor] init 失败: {e}")

    match_result: ToaMatchResult = read_toa_image(src)
    r = ToaRecognizeResult()
    r.tower_role_matrix = match_result.tower_role_matrix
    r.star_counts = match_result.star_counts
    r.match_empty = all(not (row and any(i > 0 for i in row)) for row in match_result.tower_role_matrix)

    if r.match_empty:
        return "[鸣潮]未能识别到任何角色，请确认深塔分享图完整清晰。\n"

    # OCR 提取 UID
    if match_result.uid_roi is not None:
        try:
            ocr_ret = await ocrspace([match_result.uid_roi], bot, True, language="eng", isTable=False)
            if isinstance(ocr_ret, (list, tuple)) and ocr_ret:
                p = ocr_ret[0]
                text = str(p.get("text") or "") if isinstance(p, dict) else str(p or "")
                r.recognized_uid = _parse_uid(text)
        except Exception as e:
            logger.warning(f"[ww-toa-processor] uid ocr 异常: {e}")

    season_end_time_ms = int(datetime.now().timestamp() * 1000) + 20 * 86400 * 1000
    abyss_data = build_abyss_detail_model(
        tower_role_matrix=r.tower_role_matrix,
        star_counts=r.star_counts,
        season_end_time_ms=season_end_time_ms,
    )

    # 保存到本地
    try:
        await save_abyss_detail(uid, abyss_data)
    except Exception as e:
        logger.warning(f"[ww-toa-processor] 保存深塔数据失败: {e}")

    r.summary_lines = _make_summary(r)
    logger.info("[鸣潮][深塔] " + "\n".join(r.summary_lines))

    from ..wutheringwaves_abyss.draw_abyss_card import draw_abyss_img

    return await draw_abyss_img(ev, str(uid), user_id, abyss_data=abyss_data)
