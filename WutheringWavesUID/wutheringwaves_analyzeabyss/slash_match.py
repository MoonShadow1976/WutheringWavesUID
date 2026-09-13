"""slash 分享图识别"""

import os
import re

from gsuid_core.logger import logger
import numpy as np
from PIL import Image

from ..utils.resource.RESOURCE_PATH import AVATAR_PATH, SLASH_PATH
from .match_core import (
    match_slot_best,
    pil_to_rgb_on_black,
    rgb_to_luma_np_uint8,
    safe_crop,
)

AVATAR_FOLDER_PATH = AVATAR_PATH
TOKEN_FOLDER_PATH = SLASH_PATH

_ROLE_HEAD_RE = re.compile(r"^role_head_(\d+)\.png$", re.IGNORECASE)

REF_W, REF_H = 1747, 983
REF_SLOT_W, REF_SLOT_H = 91, 91

RESONATORS_REF = [
    (1260, 416),
    (1369, 416),
    (1478, 416),
    (1260, 572),
    (1369, 572),
    (1478, 572),
]
TOKENS_REF = [(1587, 416), (1587, 572)]

REF_UID_BOX = (1525, 928, 1684, 958)
REF_SCORE1_BOX = (1060, 458, 1205, 485)
REF_SCORE2_BOX = (1060, 612, 1205, 640)

AVATAR_COMPARE_SIZE = (48, 48)
TOKEN_COMPARE_SIZE = (48, 48)

RESO_THRESHOLD = 0.10
TOKEN_THRESHOLD = 0.10

image_files: list[str] = []
img_data: list[tuple[Image.Image, np.ndarray, np.ndarray]] = []
token_files: list[str] = []
token_img: list[tuple[Image.Image, np.ndarray, np.ndarray]] = []


def _scale_box(ref_box: tuple[int, int, int, int], img_w: int, img_h: int):
    x1r, y1r, x2r, y2r = ref_box
    sx = img_w / float(REF_W)
    sy = img_h / float(REF_H)
    x1 = int(round(x1r * sx))
    y1 = int(round(y1r * sy))
    x2 = int(round(x2r * sx))
    y2 = int(round(y2r * sy))
    return x1, y1, max(1, x2 - x1), max(1, y2 - y1)


def crop_number_rois_from_image(pil_src: Image.Image) -> dict[str, Image.Image]:
    if pil_src.mode != "RGB":
        pil_src = pil_to_rgb_on_black(pil_src)
    img_arr = np.array(pil_src)
    ih, iw = img_arr.shape[0], img_arr.shape[1]

    def _crop(ref_box) -> Image.Image:
        x, y, w, h = _scale_box(ref_box, iw, ih)
        return Image.fromarray(safe_crop(img_arr, x, y, w, h))

    return {"uid": _crop(REF_UID_BOX), "score1": _crop(REF_SCORE1_BOX), "score2": _crop(REF_SCORE2_BOX)}


def init() -> None:
    image_files.clear()
    img_data.clear()
    token_files.clear()
    token_img.clear()
    if not AVATAR_FOLDER_PATH.exists():
        logger.warning(f"[share-match] avatar 目录不存在: {AVATAR_FOLDER_PATH}")
        return
    if not TOKEN_FOLDER_PATH.exists():
        logger.warning(f"[share-match] token 目录不存在: {TOKEN_FOLDER_PATH}")
        return
    for img_name in sorted(f for f in os.listdir(AVATAR_FOLDER_PATH) if f.lower().endswith(".png")):
        try:
            img = Image.open(os.path.join(AVATAR_FOLDER_PATH, img_name))
            rgb = pil_to_rgb_on_black(img).resize(AVATAR_COMPARE_SIZE, Image.Resampling.LANCZOS)
            arr = np.array(rgb)
            luma_np = rgb_to_luma_np_uint8(rgb)
            mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
            image_files.append(img_name)
            img_data.append((rgb, luma_np, mean_rgb))
        except Exception as e:
            logger.warning(f"[share-match] 加载头像模板失败 {img_name}: {e}")
    for img_name in sorted(f for f in os.listdir(TOKEN_FOLDER_PATH) if f.lower().endswith(".png")):
        try:
            img = Image.open(os.path.join(TOKEN_FOLDER_PATH, img_name))
            rgb = pil_to_rgb_on_black(img).resize(TOKEN_COMPARE_SIZE, Image.Resampling.LANCZOS)
            arr = np.array(rgb)
            luma_np = rgb_to_luma_np_uint8(rgb)
            mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
            token_files.append(img_name)
            token_img.append((rgb, luma_np, mean_rgb))
        except Exception as e:
            logger.warning(f"[share-match] 加载信物模板失败 {img_name}: {e}")


def _parse_role_file(fname: str) -> tuple[str, str]:
    m = _ROLE_HEAD_RE.match(fname)
    if m:
        cid = m.group(1)
        return cid, cid
    return "", os.path.splitext(fname)[0]


def _scale_ref_coords(img_w: int, img_h: int):
    sx = img_w / float(REF_W)
    sy = img_h / float(REF_H)
    resonators = [(int(round(x * sx)), int(round(y * sy))) for (x, y) in RESONATORS_REF]
    tokens = [(int(round(x * sx)), int(round(y * sy))) for (x, y) in TOKENS_REF]
    slot_w = int(round(REF_SLOT_W * sx))
    slot_h = int(round(REF_SLOT_H * sy))
    return resonators, tokens, slot_w, slot_h


def _match_resonator(sub_rgb: Image.Image) -> tuple[str, str, float]:
    best_idx, best_score = match_slot_best(sub_rgb, img_data, AVATAR_COMPARE_SIZE, RESO_THRESHOLD)
    if best_idx < 0:
        return "", "EMPTY_SLOT", best_score
    cid, display = _parse_role_file(image_files[best_idx])
    return cid, display, best_score


def _match_token(sub_rgb: Image.Image) -> tuple[str, float]:
    best_idx, best_score = match_slot_best(sub_rgb, token_img, TOKEN_COMPARE_SIZE, TOKEN_THRESHOLD)
    if best_idx < 0:
        return "EMPTY_SLOT", best_score
    return token_files[best_idx], best_score


class ShareMatchResult:
    def __init__(
        self,
        half_1_roles: list[tuple[str | None, str]] | None = None,
        half_2_roles: list[tuple[str | None, str]] | None = None,
        half_1_token: str | None = None,
        half_2_token: str | None = None,
        number_rois: dict[str, Image.Image] | None = None,
    ):
        self.half_1_roles = [r for r in (half_1_roles or []) if r[1] != "EMPTY_SLOT"]
        self.half_2_roles = [r for r in (half_2_roles or []) if r[1] != "EMPTY_SLOT"]
        self.half_1_token = None if half_1_token == "EMPTY_SLOT" else half_1_token
        self.half_2_token = None if half_2_token == "EMPTY_SLOT" else half_2_token
        self.number_rois: dict[str, Image.Image] | None = number_rois
        self.recognized_uid: str | None = None
        self.score_half_1: int | None = None
        self.score_half_2: int | None = None

    def is_empty(self) -> bool:
        return not self.half_1_roles and not self.half_2_roles and not self.half_1_token and not self.half_2_token

    def __str__(self) -> str:
        s1 = self.score_half_1 if self.score_half_1 is not None else "未识别"
        s2 = self.score_half_2 if self.score_half_2 is not None else "未识别"

        def _fmt(rs):
            return "、".join(n for _c, n in rs) if rs else "无"

        return (
            f"特征码: {self.recognized_uid or '未识别'}\n"
            f"队伍一: [{_fmt(self.half_1_roles)}] 分数={s1} 信物={self.half_1_token or '无'}\n"
            f"队伍二: [{_fmt(self.half_2_roles)}] 分数={s2} 信物={self.half_2_token or '无'}"
        )


def ReadWhiWaShare_image(pil_src: Image.Image) -> ShareMatchResult:
    if not img_data and not token_img:
        init()
    src_rgb = pil_to_rgb_on_black(pil_src)
    img_arr = np.array(src_rgb)
    ih, iw = img_arr.shape[0], img_arr.shape[1]

    resonators, tokens, w, h = _scale_ref_coords(iw, ih)

    role_results: list[tuple[str | None, str, float]] = []
    for x, y in resonators:
        sub_rgb = Image.fromarray(safe_crop(img_arr, x, y, w, h))
        cid, display, score = _match_resonator(sub_rgb)
        role_results.append((cid or None, display, score))

    half_1_roles = [(cid, name) for (cid, name, _s) in role_results[:3]]
    half_2_roles = [(cid, name) for (cid, name, _s) in role_results[3:]]

    res_token_raw: list[str] = []
    for x, y in tokens:
        sub_rgb = Image.fromarray(safe_crop(img_arr, x, y, w, h))
        fname, _s = _match_token(sub_rgb)
        res_token_raw.append(fname)
    half_1_token = res_token_raw[0] if len(res_token_raw) > 0 else "EMPTY_SLOT"
    half_2_token = res_token_raw[1] if len(res_token_raw) > 1 else "EMPTY_SLOT"

    try:
        rois = crop_number_rois_from_image(pil_src)
    except Exception:
        rois = None

    return ShareMatchResult(half_1_roles, half_2_roles, half_1_token, half_2_token, number_rois=rois)


def ReadWhiWaShare(WhiWaImg_PATH) -> ShareMatchResult:
    return ReadWhiWaShare_image(Image.open(WhiWaImg_PATH))
