"""矩阵分享图识别.

识别每队的角色 + buff + (第几波/第几个怪/得分), 与本地数据按 Team# 合并入库, 然后绘图.
"""

from dataclasses import dataclass, field
from datetime import datetime
import re

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from PIL import Image

from ..wutheringwaves_analyzecard.cardOCR import cut_image, cut_image_need_data
from ..wutheringwaves_analyzecard.ocrspace import ocrspace
from ..wutheringwaves_analyzecard.ScoreQuery import can_score_query_card, set_cache_score_query_card
from .abyss_data_utils import (
    build_matrix_detail_model,
    get_current_version,
    get_matrix_detail_local,
    merge_matrix_teams,
    save_matrix_detail,
)
from .matrix_match import init as matrix_init
from .matrix_match import read_matrix_image
from .slash_processor import _parse_uid

# 文件名 -> roleId
_RE_ROLE_ID = re.compile(r"(?:role_skin_)?circle_head_(\d+)\.png$", re.IGNORECASE)

# OCR 解析: "第2轮 1/5 △+226" -> round / passBoss / bossCount / score
_RE_ROUND = re.compile(r"第?\s*(\d+)\s*轮")
_RE_FRACTION = re.compile(r"(\d+)\s*/\s*(\d+)")
_RE_SCORE = re.compile(r"[+△▲▽◈◆▼▲⬡⬢]+\s*(\d+)")

# UID 裁切: 右下角, 宽 10% 高 8%
_UID_CROP_RATIOS = [(0.9, 0.92, 1.0, 1.0)]


@dataclass
class MatrixRecognizeResult:
    match_empty: bool = True
    summary_lines: list[str] = field(default_factory=list)
    recognized_uid: str | None = None
    teams: list[dict] = field(default_factory=list)  # 已 OCR 解析的 team dict


def _role_id_from_filename(fname: str) -> int:
    m = _RE_ROLE_ID.search(fname or "")
    return int(m.group(1)) if m else 0


def _parse_team_ocr(text: str, raw_team: dict) -> dict:
    """解析单个 team 的 OCR 文本 -> 填好 MatrixTeam 字段的 dict."""
    text = text or ""
    round_match = _RE_ROUND.search(text)
    frac_match = _RE_FRACTION.search(text)
    score_match = _RE_SCORE.search(text)
    # 退化: 直接从原 text 抽数字
    round_val = int(round_match.group(1)) if round_match else 1
    pass_boss = int(frac_match.group(1)) if frac_match else 0
    boss_count = int(frac_match.group(2)) if frac_match else 0
    score = int(score_match.group(1)) if score_match else 0

    # 统一头像文件名: 去掉 role_skin_ 前缀, 全部归一为 role_circle_head_{rid}.png
    role_ids = [_role_id_from_filename(f) for f in raw_team.get("Resonators", [])]
    role_icons = [f"role_circle_head_{rid}.png" for rid in role_ids]
    buff_file = raw_team.get("BUFF", "")

    return {
        "Team #": int(raw_team.get("Team #", 0)),
        "round": round_val,
        "passBoss": pass_boss,
        "bossCount": boss_count,
        "score": score,
        "roleIcons": role_icons,
        "roleList": [{"roleId": rid, "iconUrl": icon} for rid, icon in zip(role_ids, role_icons)],
        "buffs": [{"buffIcon": buff_file, "buffId": 0, "buffName": "", "desc": ""}],
    }


def _validate_and_clean(teams: list[dict]) -> list[dict]:
    """按 Team# 顺序检查波次非递减. 矩阵同波次可有多队, 允许相等; 波次倒退才丢弃."""
    last_wave = 0
    result: list[dict] = []
    for t in sorted(teams, key=lambda x: int(x.get("Team #", 0))):
        try:
            wave = int(t["round"])
        except (KeyError, TypeError, ValueError):
            wave = 0
        if wave < last_wave:
            logger.warning(f"[matrix-validate] team#{t.get('Team #')} 波次 {wave} < 前队 {last_wave}, 丢弃")
            continue
        last_wave = wave
        result.append(t)
    return result


async def run_matrix_recognize(bot: Bot, ev, images: list[Image.Image], uid: str, user_id: str) -> bytes | str:
    at = bool(ev.group_id)

    # 时限: 防止同一用户重复触发 OCR
    wait = can_score_query_card(user_id)
    if wait > 0:
        return f"[鸣潮]矩阵识别进行中，请等待{wait}秒后再试。\n"
    set_cache_score_query_card(user_id, True)
    try:
        return await _run_matrix_recognize(bot, ev, images, uid, user_id, at)
    finally:
        set_cache_score_query_card(user_id, False)


async def _run_matrix_recognize(bot, ev, images, uid, user_id, at) -> bytes | str:
    try:
        matrix_init()
    except Exception as e:
        logger.warning(f"[ww-matrix-processor] init 失败: {e}")

    r = MatrixRecognizeResult()

    # ---- 1. 逐图识别 + 收集 OCR 待识别图 ----
    all_concat_images: list[Image.Image] = []
    all_raw_teams: list[tuple[Image.Image, dict]] = []  # (原图, raw_team_dict)
    empty_team_nums: set[int] = set()  # 空队伍编号, 用于覆盖本地同位置为 None
    for idx, pil in enumerate(images):
        try:
            raw_teams = read_matrix_image(pil)
        except Exception as e:
            logger.exception(f"[ww-matrix-processor] 第{idx + 1}张图识别失败: {e}")
            continue
        if not raw_teams:
            logger.warning(f"[ww-matrix-processor] 第{idx + 1}张图未识别到任何队伍")
            continue

        for raw_team in raw_teams:
            team_num = int(raw_team.get("Team #", 0))
            # 空队伍: 不做 OCR, 仅记录编号, 合并时覆盖本地同位置为 None
            if raw_team.get("is_empty"):
                empty_team_nums.add(team_num)
                logger.info(f"[ww-matrix-processor] team#{team_num} 为空队伍, 将覆盖本地为 None")
                continue
            # 裁切 wave / monster / score 三个 bbox (绝对像素)
            try:
                wave_box = raw_team["Wave Number Area"]
                monster_box = raw_team["Monster Count Area"]
                score_box = raw_team["Team Score Area"]
                wave_img = pil.crop((wave_box[0], wave_box[1], wave_box[0] + wave_box[2], wave_box[1] + wave_box[3]))
                monster_img = pil.crop(
                    (monster_box[0], monster_box[1], monster_box[0] + monster_box[2], monster_box[1] + monster_box[3])
                )
                score_img = pil.crop((score_box[0], score_box[1], score_box[0] + score_box[2], score_box[1] + score_box[3]))
                concat = cut_image_need_data([wave_img, monster_img, score_img], direction="right")
                all_concat_images.append(concat)
                all_raw_teams.append((pil, raw_team))
            except Exception as e:
                logger.warning(f"[ww-matrix-processor] team#{team_num} 裁切失败: {e}")

    if not all_raw_teams and not empty_team_nums:
        return "[鸣潮]未能识别到任何矩阵队伍，请确认分享图完整清晰。\n"

    r.match_empty = False

    # ---- 2. 一次性 OCR 所有 team 拼接图 ----
    ocr_results = await ocrspace(all_concat_images, bot, at, language="cht", isTable=False, need_all_pass=False)
    if isinstance(ocr_results, str):
        logger.warning(f"[ww-matrix-processor] team OCR 失败: {ocr_results}")
        ocr_results = [{"error": "ocr_failed", "text": ""}] * len(all_raw_teams)

    new_teams: list[dict] = []
    for i, (_, raw_team) in enumerate(all_raw_teams):
        if i < len(ocr_results):
            text = str(ocr_results[i].get("text") or "") if isinstance(ocr_results[i], dict) else str(ocr_results[i])
        else:
            text = ""
        team_dict = _parse_team_ocr(text, raw_team)
        new_teams.append(team_dict)
        logger.debug(
            f"[ww-matrix-processor] team#{team_dict['Team #']} round={team_dict['round']} "
            f"{team_dict['passBoss']}/{team_dict['bossCount']} score={team_dict['score']} raw='{text.strip()}'"
        )

    # ---- 3. 交叉验证 (按 Team# 排序, 绝对进度严格递增) ----
    new_teams = _validate_and_clean(new_teams)

    # ---- 4. 提取 UID (取第一张图的右下角) ----
    if images:
        try:
            uid_roi_list = cut_image(images[0], _UID_CROP_RATIOS)
            uid_ret = await ocrspace(uid_roi_list, bot, at, language="eng", isTable=False, need_all_pass=False)
            if isinstance(uid_ret, list) and uid_ret:
                p = uid_ret[0]
                text = str(p.get("text") or "") if isinstance(p, dict) else str(p or "")
                r.recognized_uid = _parse_uid(text)
                logger.info(f"[ww-matrix-processor] uid OCR 原文='{text.strip()}' -> '{r.recognized_uid}'")
        except Exception as e:
            logger.warning(f"[ww-matrix-processor] uid ocr 异常: {e}")

    # 用识别到的 uid (优先于绑定的), 与 slash 一致
    if r.recognized_uid:
        if r.recognized_uid != uid:
            logger.info(f"[ww-matrix-processor] 识别到特征码 {r.recognized_uid}, 与绑定的 {uid} 不一致, 按图中特征码写入")
        uid = r.recognized_uid

    # ---- 5. 合并到本地 (考虑版本号) ----
    current_version = get_current_version()
    local_matrix, local_version = await get_matrix_detail_local(uid)
    if local_version and local_version != current_version:
        logger.info(f"[ww-matrix-processor] 版本变化 (local={local_version} != current={current_version}), 清空旧数据")
        local_teams: list[dict | None] = []
    elif local_matrix and local_matrix.modeDetails:
        # 取奇点扩张模式 teams, 转回 dict
        singularity = next((m for m in local_matrix.modeDetails if m.modeId == 1), None)
        if singularity and singularity.teams:
            local_teams = [t.model_dump() if t is not None else None for t in singularity.teams]
        else:
            local_teams = []
    else:
        local_teams = []

    merged_teams = merge_matrix_teams(local_teams, new_teams)

    # 空队伍覆盖: 本地同位置置为 None
    for team_num in empty_team_nums:
        idx = team_num - 1
        while len(merged_teams) <= idx:
            merged_teams.append(None)
        if merged_teams[idx] is not None:
            logger.info(f"[ww-matrix-processor] team#{team_num} 空队伍覆盖本地旧数据")
        merged_teams[idx] = None

    # 截断尾部空队伍 (保留中间空位占位)
    while merged_teams and (merged_teams[-1] is None or not (merged_teams[-1].get("roleIcons") or [])):
        merged_teams.pop()

    # ---- 6. 构造 MatrixData + 保存 ----
    season_end_time_ms = int(datetime.now().timestamp() * 1000) + 20 * 86400 * 1000
    matrix_data = build_matrix_detail_model(merged_teams, season_end_time_ms=season_end_time_ms)
    try:
        await save_matrix_detail(uid, matrix_data, current_version)
    except Exception as e:
        logger.warning(f"[ww-matrix-processor] 保存矩阵数据失败: {e}")

    # ---- 7. 汇总日志 ----
    r.teams = new_teams
    team_count = sum(1 for t in merged_teams if t is not None)

    def _buff_icon(t: dict) -> str:
        buffs = t.get("buffs") or []
        return buffs[0].get("buffIcon", "") if buffs else ""

    # 本次新识别的队伍
    new_lines = [f"本次识别 {len(new_teams)} 队:"]
    for t in new_teams:
        roles = [f.get("roleId") for f in (t.get("roleList") or [])]
        new_lines.append(
            f"  team#{t.get('Team #')}: 第{t.get('round')}轮 {t.get('passBoss')}/{t.get('bossCount')} "
            f"+{t.get('score')} roles={roles} buff={_buff_icon(t)}"
        )

    # 保存后的完整队伍
    save_lines = [f"矩阵保存结果: 共 {len(merged_teams)} 位, 有效 {team_count} 队"]
    for i, t in enumerate(merged_teams):
        if t is None:
            save_lines.append(f"  team#{i + 1}: [空]")
        else:
            roles = [f.get("roleId") for f in (t.get("roleList") or [])]
            save_lines.append(
                f"  team#{i + 1}: 第{t.get('round')}轮 {t.get('passBoss')}/{t.get('bossCount')} "
                f"+{t.get('score')} roles={roles} buff={_buff_icon(t)}"
            )

    summary = new_lines + save_lines
    r.summary_lines = summary
    logger.info("[鸣潮][矩阵] " + "\n".join(summary))

    # ---- 8. 绘图 ----
    from ..wutheringwaves_abyss.draw_matrix_card import draw_matrix_img

    return await draw_matrix_img(ev, str(uid), user_id, matrix_data=matrix_data)
