import os
from pathlib import Path

import numpy as np
from PIL import Image

from ..utils.resource.RESOURCE_PATH import CIRCLE_AVATAR_PATH, MATRIX_PATH
from .match_core import (
    compare_slot,
    is_gray_slot,
    pil_to_rgb_on_black,
    rgb_to_luma_np_uint8,
)

# PATH for Resonator & buff icon image data
ROUND_AVATAR_PATH = str(CIRCLE_AVATAR_PATH)

# BUFF ICON
BUFF_ICON_PATH = str(MATRIX_PATH)

# PATH for numbers
NUMBER_PATH = str(Path(__file__).parent / "number_images")

# 空位检测: luma 标准差低于此值视为空位
EMPTY_LUMA_STD_THRESHOLD = 35

# 数字模板匹配参数
NUMBER_COMPARE_SIZE = (32, 43)

# arrays for data
number_files = sorted([f for f in os.listdir(NUMBER_PATH) if f.lower().endswith(".png")])
num_data = []

image_files = sorted([f for f in os.listdir(ROUND_AVATAR_PATH) if f.lower().endswith(".png")])
img_data = []

buff_imgs = sorted([f for f in os.listdir(BUFF_ICON_PATH) if f.lower().endswith(".png")])
buff_data = []


#
# Extract team blocks
#
def is_valid_color(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    if max_val == min_val:
        h = 0.0
    elif max_val == r:
        h = (60 * ((g - b) / diff) + 360) % 360
    elif max_val == g:
        h = (60 * ((b - r) / diff) + 120) % 360
    elif max_val == b:
        h = (60 * ((r - g) / diff) + 240) % 360
    if max_val == 0:
        s = 0.0
    else:
        s = (diff / max_val) * 100
    v = max_val * 100
    return 195 < h < 215 and 17 < s < 30 and 25 < v < 40


def get_valid_blocks(img, min_pixel_size=5000):
    width, height = img.size
    pixels = img.load()
    visited = set()
    blocks = []
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 2), (0, -2), (2, 0), (-2, 0), (0, 3), (0, -3), (3, 0), (-3, 0)]
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            r, g, b = pixels[x, y]
            if is_valid_color(r, g, b):
                block_pixels = []
                queue = [(x, y)]
                visited.add((x, y))
                while queue:
                    curr_x, curr_y = queue.pop(0)
                    block_pixels.append((curr_x, curr_y))
                    for dx, dy in directions:
                        nx, ny = curr_x + dx, curr_y + dy
                        if 0 <= nx < width and 0 <= ny < height:
                            if (nx, ny) not in visited:
                                nr, ng, nb = pixels[nx, ny]
                                if is_valid_color(nr, ng, nb):
                                    visited.add((nx, ny))
                                    queue.append((nx, ny))
                if len(block_pixels) >= min_pixel_size:
                    xs = [p[0] for p in block_pixels]
                    ys = [p[1] for p in block_pixels]
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                    blocks.append({"pixel_count": len(block_pixels), "bbox": bbox, "pixels": block_pixels})

    # Merge blocks that are close or next to each other
    used = np.full(len(blocks), [False])
    res = []
    heights = []

    for i, iblock in enumerate(blocks):
        if used[i] == True:
            continue
        x0, y0, x1, y1 = iblock["bbox"][0], iblock["bbox"][1], iblock["bbox"][2], iblock["bbox"][3]
        used[i] = True
        res_curr = iblock
        heights.append(y1 - y0)

        for j, jblock in enumerate(blocks):
            if used[j] == True:
                continue
            xx0, yy0, xx1, yy1 = jblock["bbox"][0], jblock["bbox"][1], jblock["bbox"][2], jblock["bbox"][3]
            if abs(y0 - yy0) <= 3 and abs(y1 - yy1) <= 3 and (abs(x1 - xx0) <= 5 or x1 > xx0):
                res_curr["pixel_count"] = res_curr["pixel_count"] + jblock["pixel_count"]
                res_curr["bbox"] = (min(x0, xx0), y0, max(x1, xx1), y1)
                x0, y0, x1, y1 = res_curr["bbox"][0], res_curr["bbox"][1], res_curr["bbox"][2], res_curr["bbox"][3]
                used[j] = True

        res.append(res_curr)

    # Height < most common, increase bbox from top / bottom based on position
    most_common_height = max(set(heights), key=heights.count)
    count = 0
    for num in heights:
        if num == most_common_height:
            count = count + 1
    if count == 1:
        most_common_height = int(np.median(heights) + 0.5)

    for i, height in enumerate(heights):
        if height < most_common_height and most_common_height - height >= 2:
            if res[i]["bbox"][1] < img.size[1] // 2:
                res[i]["bbox"] = [
                    res[i]["bbox"][0],
                    max(0, res[i]["bbox"][1] - most_common_height + height),
                    res[i]["bbox"][2],
                    res[i]["bbox"][3],
                ]
            else:
                res[i]["bbox"] = [
                    res[i]["bbox"][0],
                    res[i]["bbox"][1],
                    res[i]["bbox"][2],
                    min(img.size[1], res[i]["bbox"][3] + most_common_height - height),
                ]

    return res


def to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    diff = max_val - min_val
    if max_val == min_val:
        h = 0.0
    elif max_val == r:
        h = (60 * ((g - b) / diff) + 360) % 360
    elif max_val == g:
        h = (60 * ((b - r) / diff) + 120) % 360
    elif max_val == b:
        h = (60 * ((r - g) / diff) + 240) % 360
    if max_val == 0:
        s = 0.0
    else:
        s = (diff / max_val) * 100
    v = max_val * 100
    return h, s, v


def init(force: bool = False) -> None:
    if not force and num_data and img_data and buff_data:
        return
    num_data.clear()
    img_data.clear()
    buff_data.clear()
    # Read number templates
    for img_name in number_files:
        img_ava = Image.open(os.path.join(NUMBER_PATH, img_name))
        rgb = pil_to_rgb_on_black(img_ava).resize(NUMBER_COMPARE_SIZE, Image.Resampling.LANCZOS)
        arr = np.array(rgb)
        luma_np = rgb_to_luma_np_uint8(rgb)
        mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
        num_data.append((rgb, luma_np, mean_rgb))

    # Read resonator icons
    for img_name in image_files:
        img_ava = Image.open(os.path.join(ROUND_AVATAR_PATH, img_name))
        rgb = pil_to_rgb_on_black(img_ava).resize((128, 128), Image.Resampling.LANCZOS)
        arr = np.array(rgb)[2:124, 0:127]
        rgb = Image.fromarray(arr)
        luma_np = rgb_to_luma_np_uint8(rgb)
        mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
        img_data.append((rgb, luma_np, mean_rgb))

    # Read BUFF icons
    for img_name in buff_imgs:
        img_ava = Image.open(os.path.join(BUFF_ICON_PATH, img_name))
        rgb = pil_to_rgb_on_black(img_ava).resize((75, 75), Image.Resampling.LANCZOS)
        arr = np.array(rgb)
        luma_np = rgb_to_luma_np_uint8(rgb)
        mean_rgb = arr.reshape(-1, 3).mean(axis=0).astype(np.float64)
        buff_data.append((rgb, luma_np, mean_rgb))


def ReadMatrixImg(Matrix_Img_PATH):
    """原脚本主入口. 输入支持路径或 PIL.Image."""
    if isinstance(Matrix_Img_PATH, (str, Path)):
        img = Image.open(Matrix_Img_PATH).convert("RGB")
    else:
        img = Matrix_Img_PATH.convert("RGB") if Matrix_Img_PATH.mode != "RGB" else Matrix_Img_PATH

    hsv_img = img.convert("HSV")
    hsv_data = np.array(hsv_img)
    rgb_data = np.array(img)

    # Light gray -> gray
    lower = np.array([203 * 255 / 360, 21 * 255 / 100, 48 * 255 / 100])
    upper = np.array([207 * 255 / 360, 25 * 255 / 100, 52 * 255 / 100])
    mask = np.all((hsv_data >= lower) & (hsv_data <= upper), axis=-1)
    rgb_data[mask] = np.array([61, 72, 80])
    img = Image.fromarray(rgb_data)

    res = get_valid_blocks(img)

    res_img = []

    for index, one_team in enumerate(res):
        team_to_test = np.array(img)[res[index]["bbox"][1] : res[index]["bbox"][3], res[index]["bbox"][0] : res[index]["bbox"][2]]

        h_block = team_to_test.shape[0]
        # remove blocks that are not valid / change constant parameters
        if team_to_test.shape[1] < img.size[0] // 3:
            continue

        # team number 完全由 OCR 识别, 不再做数字模板匹配
        res_numbers = 0

        # Identify resonator
        start_pos = [159 * h_block // 122, 0]

        grayBar_pos = 0

        # Locate the bar right next to 3 resonators
        for i in range(start_pos[0], h_block * 5):
            count = 0
            for j in range(0, h_block):
                pixel_rgb = team_to_test[j][i]
                h, s, v = to_hsv(pixel_rgb[0], pixel_rgb[1], pixel_rgb[2])
                if 200 < h < 210 and 5 < s < 15 and 40 < v < 60:
                    count = count + 1
            if count > h_block // 4:
                grayBar_pos = i
                break

        area_w, area_h = 366 * h_block // 122, h_block

        three_resonator_block = team_to_test[
            start_pos[1] : start_pos[1] + area_h, start_pos[0] : grayBar_pos - int(h_block * 0.1)
        ]

        # Divide to 3 resonators
        avatar_w = three_resonator_block.shape[1] // 3

        resonator_in_team = []

        for i in range(3):
            sub_image = three_resonator_block[0 : three_resonator_block.shape[0], avatar_w * i : avatar_w * (i + 1)]
            resonator_in_team.append(sub_image)

        # Compare each resonator w/ database
        AVATAR_COMPARE_SIZE = (127, 122)

        res_resonator = []

        for i, resonator_avatar in enumerate(resonator_in_team):
            ava_img = Image.fromarray(resonator_avatar)

            # 空位检测: luma 标准差判断, 空位直接标记 empty.webp 跳过
            if is_gray_slot(ava_img, AVATAR_COMPARE_SIZE, EMPTY_LUMA_STD_THRESHOLD):
                res_resonator.append("empty.webp")
                continue

            ava_arr = np.array(ava_img.resize(AVATAR_COMPARE_SIZE, Image.Resampling.LANCZOS))

            best_score = -1.0
            best_idx = 0
            for idx, tpl in enumerate(img_data):
                final, _, _, _ = compare_slot(ava_img, tpl, AVATAR_COMPARE_SIZE)
                if final > best_score:
                    best_score = final
                    best_idx = idx

            res_resonator.append(image_files[best_idx])

        # Identify BUFF
        buff_x0 = grayBar_pos + 27 * h_block // 122

        buff_w, buff_h = 75 * h_block // 122, 75 * h_block // 122

        buff_icon = team_to_test[(h_block - buff_h) // 2 : (h_block + buff_h) // 2, buff_x0 : buff_x0 + buff_w]

        BUFF_COMPARE_SIZE = (75, 75)

        buff_img = Image.fromarray(buff_icon)

        buff_arr = np.array(buff_img.resize(BUFF_COMPARE_SIZE, Image.Resampling.LANCZOS))

        best_score = -1.0
        best_idx = 0
        for idx, tpl in enumerate(buff_data):
            final, _, _, _ = compare_slot(buff_img, tpl, BUFF_COMPARE_SIZE)
            if final > best_score:
                best_score = final
                best_idx = idx

        # Bounding box for wave info & score
        # team number 区域 (合并十位+个位), 供 processor 裁切 OCR
        team_number_area = [
            res[index]["bbox"][0] + 33 * h_block // 118,
            res[index]["bbox"][1] + h_block // 2 - 21 * h_block // 118,
            65 * h_block // 118,
            45 * h_block // 118,
        ]
        wave_number = [
            res[index]["bbox"][0] + (grayBar_pos + team_to_test.shape[1]) // 2 - int(h_block * 1.2),
            res[index]["bbox"][1] + h_block // 6,
            int(h_block * 1.2),
            h_block // 3,
        ]
        monster_count = [
            res[index]["bbox"][0] + (grayBar_pos + team_to_test.shape[1]) // 2 - h_block * 2 // 3,
            res[index]["bbox"][1] + h_block // 2,
            h_block * 2 // 3,
            h_block // 2,
        ]
        team_score = [
            res[index]["bbox"][0] + team_to_test.shape[1] - int(h_block * 2),
            res[index]["bbox"][1] + h_block // 3,
            int(h_block * 2),
            h_block // 3,
        ]

        # 空队伍也返回, 标记 is_empty, 由调用方决定是否覆盖本地数据
        is_empty = "empty.webp" in res_resonator
        res_img.append(
            {
                "Team #": res_numbers,
                "Resonators": res_resonator,
                "BUFF": buff_imgs[best_idx],
                "Team Number Area": team_number_area,
                "Wave Number Area": wave_number,
                "Monster Count Area": monster_count,
                "Team Score Area": team_score,
                "is_empty": is_empty,
            }
        )

    return res_img


def match_team_number(pil_img: Image.Image, h_block: int) -> int:
    """数字模板匹配 team number. 输入 team number 区域的裁切图, 返回两位数."""
    num_img = pil_img.resize(NUMBER_COMPARE_SIZE, Image.Resampling.LANCZOS)
    best_score = -1.0
    best_idx = 0
    for idx, tpl in enumerate(num_data):
        final, _, _, _ = compare_slot(num_img, tpl, NUMBER_COMPARE_SIZE)
        if final > best_score:
            best_score = final
            best_idx = idx
    return int(number_files[best_idx].split(".")[0])


# wwuid 兼容别名
read_matrix_image = ReadMatrixImg
