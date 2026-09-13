"""slash 分享图处理"""

from dataclasses import dataclass, field
from datetime import datetime
import re

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from PIL import Image

from ..wutheringwaves_analyzecard.ocrspace import ocrspace
from ..wutheringwaves_analyzecard.ScoreQuery import can_score_query_card, set_cache_score_query_card
from .abyss_data_utils import build_slash_detail_model
from .slash_match import ReadWhiWaShare_image, ShareMatchResult, init

_RE_LONG = re.compile(r"\b(\d{6,15})\b")
_RE_SHORT = re.compile(r"(\d{1,6})")


def _s2d(text: str) -> str:
    """全角转半角"""
    if not text:
        return ""
    text = re.sub(r"[０-９]", lambda x: chr(ord(x.group(0)) - 0xFEE0), text)
    text = re.sub(r"[Ａ-Ｚａ-ｚ]", lambda x: chr(ord(x.group(0)) - 0xFEE0), text)
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]", "", text)
    return text.strip()


def _parse_uid(text: str) -> str | None:
    """从 OCR 文本中提取 9 位 UID, 非 9 位视为未识别."""
    raw = _s2d(text or "")
    cand: list[str] = []
    cand.extend(_RE_LONG.findall(raw))
    merged = re.sub(r"[\s\-_.,;:|/\\()\[\]]+", "", raw)
    cand.extend(_RE_LONG.findall(merged))
    only = "".join(c for c in raw if c.isdigit())
    if len(only) >= 6:
        cand.append(only)
    if not cand:
        return None
    u = list(dict.fromkeys(cand))
    # 严格要求 9 位
    pref9 = [c for c in u if len(c) == 9]
    return pref9[0] if pref9 else None


def _parse_score(text: str) -> int | None:
    s = _s2d(text or "")
    norm = re.sub(r"[,\s]+", "", s)
    if "." in norm:
        norm = norm.split(".")[0]
    cand = _RE_SHORT.findall(norm) or _RE_SHORT.findall(s)
    best: int | None = None
    for c in cand:
        n = int(c)
        if 0 <= n <= 999999 and (best is None or n > best):
            best = n
    return best


@dataclass
class SlashRecognizeResult:
    match_empty: bool = True
    summary_lines: list[str] = field(default_factory=list)
    recognized_uid: str | None = None
    score_half_1: int | None = None
    score_half_2: int | None = None
    slash_dict: dict | None = None
    token_files: list[str] = field(default_factory=list)
    half_char_names: list[list[str]] = field(default_factory=list)


def _make_summary(r: SlashRecognizeResult) -> list[str]:
    s1 = r.score_half_1 if r.score_half_1 is not None else 0
    s2 = r.score_half_2 if r.score_half_2 is not None else 0
    total = "未识别"
    if r.score_half_1 is not None and r.score_half_2 is not None:
        total = str(r.score_half_1 + r.score_half_2)
    uid = r.recognized_uid or "未识别"
    lines = [f"特征码: {uid}  总分: {total}"]
    for idx, names in enumerate(r.half_char_names, 1):
        names_line = "、".join(names) if names else "无"
        sc = s1 if idx == 1 else s2
        tk = r.token_files[idx - 1] if idx - 1 < len(r.token_files) else "无"
        lines.append(f"  队伍{idx}: [{names_line}]  分数: {sc}  信物: {tk}")
    return lines


async def run_full_slash_recognize(
    bot: Bot,
    ev_user_id: str,
    at_sender: bool,
    src: Image.Image,
) -> tuple[SlashRecognizeResult, ShareMatchResult] | str:
    """匹配 -> OCR -> 拼 slash_dict"""
    # 时限: 防止同一用户重复触发 OCR (整个识别+绘图期间阻断)
    wait = can_score_query_card(ev_user_id)
    if wait > 0:
        return f"[鸣潮]海墟识别进行中，请等待{wait}秒后再试。\n"
    set_cache_score_query_card(ev_user_id, True)
    try:
        return await _run_slash_recognize(bot, ev_user_id, at_sender, src)
    finally:
        set_cache_score_query_card(ev_user_id, False)


async def _run_slash_recognize(bot, ev_user_id, at_sender, src) -> tuple[SlashRecognizeResult, ShareMatchResult]:
    try:
        init()
    except Exception as e:
        logger.warning(f"[ww-slash-processor] init 失败: {e}")
    share_result: ShareMatchResult = ReadWhiWaShare_image(src)
    r = SlashRecognizeResult()
    r.match_empty = share_result.is_empty()
    for half_roles, half_tok in [
        (share_result.half_1_roles, share_result.half_1_token),
        (share_result.half_2_roles, share_result.half_2_token),
    ]:
        r.half_char_names.append([name for _cid, name in half_roles if name])
        r.token_files.append(half_tok or "")

    rois = getattr(share_result, "number_rois", None)
    if rois and rois.get("uid") and rois.get("score1") and rois.get("score2"):
        images = [rois["uid"], rois["score1"], rois["score2"]]
        ocr_ret = None
        try:
            ocr_ret = await ocrspace(images, bot, at_sender, language="eng", isTable=False)
        except Exception as e:
            logger.exception(f"[ww-slash-processor] ocrspace 异常: {e}")
        if isinstance(ocr_ret, str):
            r.summary_lines = [f"[OCR_ERROR]{ocr_ret}"]
            return r, share_result
        if isinstance(ocr_ret, (list, tuple)) and ocr_ret:

            def _t(i):
                p = ocr_ret[i] if i < len(ocr_ret) else None
                if isinstance(p, dict):
                    return str(p.get("text") or "")
                if isinstance(p, str):
                    return p
                return ""

            r.recognized_uid = _parse_uid(_t(0))
            r.score_half_1 = _parse_score(_t(1))
            r.score_half_2 = _parse_score(_t(2))

    share_result.recognized_uid = r.recognized_uid
    share_result.score_half_1 = r.score_half_1
    share_result.score_half_2 = r.score_half_2

    if not r.match_empty:
        halves_raw = [share_result.half_1_roles, share_result.half_2_roles]
        tokens_raw = [share_result.half_1_token, share_result.half_2_token]
        scores = [
            r.score_half_1 if r.score_half_1 is not None else 0,
            r.score_half_2 if r.score_half_2 is not None else 0,
        ]
        half_char_ids: list[list[int]] = []
        half_buff_icons: list[str] = []
        for roles_raw, tok in zip(halves_raw, tokens_raw):
            ids = []
            for cid, _cname in roles_raw:
                n = int(cid) if cid is not None and str(cid).isdigit() else 0
                if n > 0:
                    ids.append(n)
            half_char_ids.append(ids)
            half_buff_icons.append(tok if tok and tok != "EMPTY_SLOT" else "")

        now = datetime.now()
        from ..wutheringwaves_abyss.draw_slash_info import get_slash_schedule

        schedule_data = await get_slash_schedule()
        sorted_ids = sorted(schedule_data, key=int)
        current_id = next(
            (
                s
                for s in sorted_ids
                if datetime.strptime(schedule_data[s]["begin"], "%Y-%m-%d")
                <= now
                <= datetime.strptime(schedule_data[s]["end"], "%Y-%m-%d")
            ),
            next((s for s in sorted_ids if datetime.strptime(schedule_data[s]["begin"], "%Y-%m-%d") > now), sorted_ids[-1]),
        )
        season_end_time_ms = int(datetime.strptime(schedule_data[current_id]["end"], "%Y-%m-%d").timestamp() * 1000)

        detail = build_slash_detail_model(
            half_char_ids=half_char_ids,
            half_scores=scores,
            half_buff_icons=half_buff_icons,
            challenge_id=12,
            challenge_name="无尽湍渊",
            season_end_time_ms=season_end_time_ms,
        )
        extra = {
            "tokenFiles": list(r.token_files),
            "charNamesList": [list(x) for x in r.half_char_names],
        }
        r.slash_dict = detail.model_dump()
        r.slash_dict.update(extra)
    r.summary_lines = _make_summary(r)
    return r, share_result
