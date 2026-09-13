"""海墟 / 深塔 分享图通用图像匹配原语.

NCC(亮度结构) + 颜色相似度 的混合匹配，供 share_match(海墟) 与 toa_match(深塔) 复用。
"""

import numpy as np
from PIL import Image

STRUCT_WEIGHT = 0.70
COLOR_WEIGHT = 0.30
PIXEL_RGB_RATIO = 0.7
PIXEL_RGB_THRESHOLD = 30
PIXEL_RGB_BG_THRESHOLD = 60


def pil_to_rgb_on_black(img: Image.Image) -> Image.Image:
    if img.mode not in ("RGBA", "RGB", "LA", "P", "L"):
        img = img.convert("RGBA")
    if img.mode == "P":
        img = img.convert("RGBA")
    if img.mode == "LA":
        img = img.convert("RGBA")
    if img.mode == "L":
        return img.convert("RGB")
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[3])
        return bg
    return img.convert("RGB")


def rgb_to_luma_np_uint8(rgb_pil: Image.Image) -> np.ndarray:
    arr = np.array(rgb_pil, dtype=np.float64)
    luma = arr[..., 0] * 0.2989 + arr[..., 1] * 0.5870 + arr[..., 2] * 0.1140
    return np.clip(luma, 0, 255).astype(np.uint8)


def safe_crop(img_arr: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    ih, iw = img_arr.shape[0], img_arr.shape[1]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(iw, x + w), min(ih, y + h)
    if x1 <= x0 or y1 <= y0:
        if len(img_arr.shape) == 3:
            return np.zeros((max(1, h), max(1, w), img_arr.shape[2]), dtype=img_arr.dtype)
        return np.zeros((max(1, h), max(1, w)), dtype=img_arr.dtype)
    crop = img_arr[y0:y1, x0:x1]
    if crop.shape[0] != h or crop.shape[1] != w:
        pad_y0 = y0 - y
        pad_x0 = x0 - x
        if len(img_arr.shape) == 3:
            full = np.zeros((h, w, img_arr.shape[2]), dtype=img_arr.dtype)
        else:
            full = np.zeros((h, w), dtype=img_arr.dtype)
        full[pad_y0 : pad_y0 + crop.shape[0], pad_x0 : pad_x0 + crop.shape[1]] = crop
        return full
    return crop


def is_gray_slot(sub_rgb_pil: Image.Image, compare_size: tuple[int, int], std_thr: int = 35) -> bool:
    """空位检测: luma 标准差低于阈值视为空位 (灰色背景无细节). 矩阵+深塔共用."""
    arr = np.array(sub_rgb_pil.resize(compare_size, Image.Resampling.LANCZOS))
    luma = arr[:, :, 0] * 0.299 + arr[:, :, 1] * 0.587 + arr[:, :, 2] * 0.114
    return float(luma.std()) < std_thr


def is_slot_empty(rgb_arr: np.ndarray, black_thr: int = 50, empty_pct_thr: int = 80) -> bool:
    is_black = np.all(rgb_arr < black_thr, axis=2)
    tot = rgb_arr.shape[0] * rgb_arr.shape[1]
    return 100.0 * float(np.sum(is_black)) / float(tot) > empty_pct_thr


def ncc_uint8(a: np.ndarray, b: np.ndarray) -> float:
    af = a.astype(np.float64)
    bf = b.astype(np.float64)
    am = af - af.mean()
    bm = bf - bf.mean()
    denom_a = np.sqrt(np.sum(am * am))
    denom_b = np.sqrt(np.sum(bm * bm))
    if denom_a < 1e-9 or denom_b < 1e-9:
        return 0.0
    return max(-1.0, min(1.0, float(np.sum(am * bm) / (denom_a * denom_b))))


def align_shapes_uint8(a_np: np.ndarray, b_np: np.ndarray, target_size_wh: tuple[int, int]):
    tw, th = target_size_wh

    def _to_size(src: np.ndarray) -> np.ndarray:
        if src.shape == (th, tw):
            return src
        return np.array(Image.fromarray(src).resize((tw, th), Image.Resampling.LANCZOS), dtype=np.uint8)

    return _to_size(a_np), _to_size(b_np)


def diff_int(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.abs(a.astype(np.int32) - b.astype(np.int32))


def pixel_rgb_similarity(arr1: np.ndarray, arr2: np.ndarray) -> float:
    r1, g1, b1 = arr1[:, :, 0], arr1[:, :, 1], arr1[:, :, 2]
    bg_mask = (r1 < PIXEL_RGB_BG_THRESHOLD) & (g1 < PIXEL_RGB_BG_THRESHOLD) & (b1 < PIXEL_RGB_BG_THRESHOLD)
    fg_mask = ~bg_mask
    if not np.any(fg_mask):
        return 0.0
    r2, g2, b2 = arr2[:, :, 0], arr2[:, :, 1], arr2[:, :, 2]
    dr = diff_int(r1, r2)
    dg = diff_int(g1, g2)
    db = diff_int(b1, b2)
    matches = (dr < PIXEL_RGB_THRESHOLD) & (dg < PIXEL_RGB_THRESHOLD) & (db < PIXEL_RGB_THRESHOLD)
    n_match = int(np.sum(matches & fg_mask))
    n_tot = int(np.sum(fg_mask))
    return float(n_match) / float(n_tot) if n_tot else 0.0


def avg_rgb_similarity(mean1: np.ndarray, mean2: np.ndarray) -> float:
    diff_norm = float(np.mean(np.abs(mean1 - mean2))) / 255.0
    return float(np.exp(-diff_norm * 4.0))


def compare_slot(
    sub_rgb_pil: Image.Image,
    template_tuple: tuple[Image.Image, np.ndarray, np.ndarray],
    target_size_wh: tuple[int, int],
) -> tuple[float, float, float, float]:
    """混合匹配: NCC(亮度) * STRUCT_WEIGHT + color_score * COLOR_WEIGHT.
    返回 (final, ncc_raw, color_pixel, color_avg)."""
    tpl_rgb_pil, tpl_luma_np, tpl_mean_rgb = template_tuple

    if sub_rgb_pil.size != target_size_wh:
        sub_rgb_pil = sub_rgb_pil.resize(target_size_wh, Image.Resampling.LANCZOS)
    sub_rgb_arr = np.array(sub_rgb_pil)
    sub_luma_np = rgb_to_luma_np_uint8(sub_rgb_pil)
    sub_mean_rgb = sub_rgb_arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
    tpl_rgb_arr = np.array(tpl_rgb_pil)

    sub_luma_al, tpl_luma_al = align_shapes_uint8(sub_luma_np, tpl_luma_np, target_size_wh)
    ncc_raw = ncc_uint8(sub_luma_al, tpl_luma_al)
    ncc_01 = 0.5 * (ncc_raw + 1.0)

    color_pixel = pixel_rgb_similarity(sub_rgb_arr, tpl_rgb_arr)
    color_avg = avg_rgb_similarity(sub_mean_rgb, tpl_mean_rgb)
    color_score = PIXEL_RGB_RATIO * color_pixel + (1.0 - PIXEL_RGB_RATIO) * color_avg

    final = STRUCT_WEIGHT * ncc_01 + COLOR_WEIGHT * color_score
    return float(final), ncc_raw, color_pixel, color_avg


def match_slot_best(
    sub_rgb: Image.Image,
    templates: list,
    compare_size: tuple[int, int],
    empty_threshold: float,
) -> tuple[int, float]:
    """在 templates 中找最佳匹配; 空槽或低于阈值返回 (-1, score)."""
    probe_arr = np.array(sub_rgb.resize(compare_size, Image.Resampling.LANCZOS))
    if is_slot_empty(probe_arr):
        return -1, 0.0
    best_score = -1.0
    best_idx = 0
    for idx, tpl in enumerate(templates):
        final, _, _, _ = compare_slot(sub_rgb, tpl, compare_size)
        if final > best_score:
            best_score = final
            best_idx = idx
    if best_score < empty_threshold:
        return -1, float(best_score)
    return best_idx, float(best_score)
