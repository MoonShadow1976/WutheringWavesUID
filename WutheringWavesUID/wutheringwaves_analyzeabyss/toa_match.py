"""深塔 (ToA) 分享图识别.

复用 match_core 的图像匹配原语, 仅保留深塔专属坐标与圆形头像模板。
输出角色矩阵 + UID 截图 + 星级, 行顺序:
  row0 -> 塔1(残响之塔) 4层
  row1 -> 塔3(回音之塔) 4层
  row2-5 -> 塔2(深境之塔) 1-4层
"""

from dataclasses import dataclass, field
import os
import re

from gsuid_core.logger import logger
import numpy as np
from PIL import Image

from ..utils.resource.RESOURCE_PATH import CIRCLE_AVATAR_PATH
from .match_core import (
    match_slot_best,
    pil_to_rgb_on_black,
    rgb_to_luma_np_uint8,
    safe_crop,
)

CIRCLE_AVATAR_FOLDER = CIRCLE_AVATAR_PATH

_CIRCLE_ROLE_RE = re.compile(r"(?:role_skin_)?circle_head_(\d+)\.png$", re.IGNORECASE)

# 角色识别参考分辨率 (与原 ToAReader 一致)
REF_W, REF_H = 1747, 983
REF_SLOT_W, REF_SLOT_H = 71, 71
AVATAR_COMPARE_SIZE = (71, 71)
RESO_THRESHOLD = 0.10

# 空位检测: luma 标准差低于此值视为空位 (空位~24, 最低角色~41)
EMPTY_LUMA_STD_THRESHOLD = 35

# 18 个槽位, 按行排列: 6 行 x 3 列
RESONATORS_REF = [
    (937, 386),
    (1020, 386),
    (1103, 386),
    (937, 526),
    (1020, 526),
    (1103, 526),
    (1397, 386),
    (1480, 386),
    (1563, 386),
    (1397, 486),
    (1480, 486),
    (1563, 486),
    (1397, 586),
    (1480, 586),
    (1563, 586),
    (1397, 686),
    (1480, 686),
    (1563, 686),
]

# UID 区域 (用户实测 1760x995, 转换到 1747x983)
# 原始: 左上(1530,925) 右下(1693,966)
REF_UID_BOX = (1519, 914, 1681, 954)

# 星级区域: 相对每层第一个角色的偏移 (1747x983 坐标系)
# 用户实测塔1-4层: 星1 左上(817,416) 右下(841,438) in 1760x995
# 角色1 位置(937,386) -> 转换后星1(811,411)-(835,433)
# 偏移: dx=-126, dy=25, 宽24, 高22, 星间距33
STAR_OFFSET_X = -126  # 星1左边缘相对角色左边缘
STAR_OFFSET_Y = 25  # 星1上边缘相对角色上边缘
STAR_WIDTH = 24
STAR_HEIGHT = 22
STAR_GAP = 33  # 相邻星左边缘间距
STAR_SUM_THRESHOLD = 200  # 亮星 RGB sum 阈值

image_files: list[str] = []
img_data: list[tuple[Image.Image, np.ndarray, np.ndarray]] = []


@dataclass
class ToaMatchResult:
    tower_role_matrix: list[list[int]] = field(default_factory=list)
    star_counts: list[int] = field(default_factory=list)  # 6 行各自的星级 0-3
    uid_roi: Image.Image | None = None


def _scale_ref_coords(img_w: int, img_h: int):
    sx = img_w / float(REF_W)
    sy = img_h / float(REF_H)
    resonators = [(int(round(x * sx)), int(round(y * sy))) for (x, y) in RESONATORS_REF]
    slot_w = int(round(REF_SLOT_W * sx))
    slot_h = int(round(REF_SLOT_H * sy))
    return resonators, slot_w, slot_h, sx, sy


def _scale_box(ref_box: tuple[int, int, int, int], img_w: int, img_h: int):
    x1r, y1r, x2r, y2r = ref_box
    sx = img_w / float(REF_W)
    sy = img_h / float(REF_H)
    x1 = int(round(x1r * sx))
    y1 = int(round(y1r * sy))
    x2 = int(round(x2r * sx))
    y2 = int(round(y2r * sy))
    return x1, y1, max(1, x2 - x1), max(1, y2 - y1)


def init() -> None:
    image_files.clear()
    img_data.clear()
    if not CIRCLE_AVATAR_FOLDER.exists():
        logger.warning(f"[toa-match] circle avatar 目录不存在: {CIRCLE_AVATAR_FOLDER}")
        return
    for img_name in sorted(f for f in os.listdir(CIRCLE_AVATAR_FOLDER) if f.lower().endswith(".png")):
        try:
            img = Image.open(os.path.join(CIRCLE_AVATAR_FOLDER, img_name))
            rgb = pil_to_rgb_on_black(img).resize(AVATAR_COMPARE_SIZE, Image.Resampling.LANCZOS)
            arr = np.array(rgb)
            luma_np = rgb_to_luma_np_uint8(rgb)
            mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
            image_files.append(img_name)
            img_data.append((rgb, luma_np, mean_rgb))
        except Exception as e:
            logger.warning(f"[toa-match] 加载圆形头像模板失败 {img_name}: {e}")


def _parse_role_id(fname: str) -> int:
    m = _CIRCLE_ROLE_RE.search(fname)
    if m:
        return int(m.group(1))
    return 0


def _is_gray_slot(sub_rgb: Image.Image) -> bool:
    """检测空位: luma 标准差低 (空位细节少, std~24; 角色头像 std>40)."""
    arr = np.array(sub_rgb.resize(AVATAR_COMPARE_SIZE, Image.Resampling.LANCZOS))
    luma = arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114
    return float(luma.std()) < EMPTY_LUMA_STD_THRESHOLD


def _match_resonator(sub_rgb: Image.Image) -> tuple[int, float]:
    # 灰色空位直接返回 0, 不依赖 test.png 模板
    if _is_gray_slot(sub_rgb):
        return 0, 0.0
    best_idx, best_score = match_slot_best(sub_rgb, img_data, AVATAR_COMPARE_SIZE, RESO_THRESHOLD)
    if best_idx < 0:
        return 0, best_score
    return _parse_role_id(image_files[best_idx]), best_score


def _detect_row_stars(img_arr: np.ndarray, role_x: int, role_y: int, sx: float, sy: float) -> int:
    """检测一行(一层)的星级, 返回 0-3.

    三颗星水平排列在第一个角色左边, 亮星 RGB sum 大于阈值。
    """
    star_w = int(round(STAR_WIDTH * sx))
    star_h = int(round(STAR_HEIGHT * sy))
    gap = int(round(STAR_GAP * sx))
    base_x = role_x + int(round(STAR_OFFSET_X * sx))
    base_y = role_y + int(round(STAR_OFFSET_Y * sy))

    star_count = 0
    for i in range(3):
        x = base_x + i * gap
        region = safe_crop(img_arr, x, base_y, star_w, star_h)
        if region.size == 0:
            continue
        avg = region.reshape(-1, 3).mean(axis=0)
        rgb_sum = int(avg[0]) + int(avg[1]) + int(avg[2])
        logger.debug(
            f"[toa-star] row star{i + 1}: pos=({x},{base_y}) "
            f"avg=({avg[0]:.0f},{avg[1]:.0f},{avg[2]:.0f}) sum={rgb_sum} "
            f"{'LIT' if rgb_sum > STAR_SUM_THRESHOLD else 'dark'}"
        )
        if rgb_sum > STAR_SUM_THRESHOLD:
            star_count += 1
    return star_count


def crop_uid_roi(pil_src: Image.Image) -> Image.Image | None:
    img_arr = np.array(pil_to_rgb_on_black(pil_src))
    ih, iw = img_arr.shape[0], img_arr.shape[1]
    x, y, w, h = _scale_box(REF_UID_BOX, iw, ih)
    return Image.fromarray(safe_crop(img_arr, x, y, w, h))


def read_toa_image(pil_src: Image.Image) -> ToaMatchResult:
    """识别深塔分享图, 返回角色矩阵 + 星级 + UID 截图."""
    if not img_data:
        init()
    src_rgb = pil_to_rgb_on_black(pil_src)
    img_arr = np.array(src_rgb)
    ih, iw = img_arr.shape[0], img_arr.shape[1]
    logger.info(f"[toa-match] image size: {iw}x{ih}")

    resonators, w, h, sx, sy = _scale_ref_coords(iw, ih)

    res: list[int] = []
    for idx, (x, y) in enumerate(resonators):
        sub_rgb = Image.fromarray(safe_crop(img_arr, x, y, w, h))
        role_id, score = _match_resonator(sub_rgb)
        if role_id:
            logger.debug(f"[toa-match] slot{idx} ({x},{y}) -> role {role_id} (score={score:.3f})")
        res.append(role_id)

    matrix = [res[i * 3 : (i + 1) * 3] for i in range(6)]

    # 每行(层)第一个角色位置, 用于星级检测
    row_first_roles = [resonators[i * 3] for i in range(6)]
    star_counts = [_detect_row_stars(img_arr, x, y, sx, sy) for x, y in row_first_roles]

    uid_roi = crop_uid_roi(pil_src)

    return ToaMatchResult(tower_role_matrix=matrix, star_counts=star_counts, uid_roi=uid_roi)
