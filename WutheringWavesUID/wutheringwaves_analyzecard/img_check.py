# change from https://github.com/TedIwaArdN/wuwabot_reader

from venv import logger
import numpy as np
from PIL import Image

from ..utils.image import TEXT_PATH
from ..utils.resource.RESOURCE_PATH import PHANTOM_PATH
from ..utils.ascension.echo import get_echo_ids_by_set_name

ECHO_SIZE = (8, 8)
SET_SIZE = (8, 8)


# 加载模板图像的函数
def load_template_images() -> tuple[dict[str, Image.Image], dict[str, Image.Image]]:
    """加载声骸和套装模板图像"""
    templates_phantom = {}
    templates_set = {}

    # 加载声骸模板
    phantom_path = PHANTOM_PATH
    if phantom_path.exists():
        for file in phantom_path.glob("*.png"):
            try:
                img = Image.open(file)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                # 预缩放到32x32用于声骸比较
                img = img.resize(ECHO_SIZE, Image.Resampling.LANCZOS)
                templates_phantom[file.stem.replace("phantom_", "")] = img
            except Exception as e:
                print(f"加载声骸模板 {file} 失败: {e}")

    # 加载套装模板
    attribute_path = TEXT_PATH / "attribute_effect"
    if attribute_path.exists():
        for file in attribute_path.glob("*.png"):
            try:
                img = Image.open(file)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                # 预缩放到8x8用于套装比较
                img = img.resize(SET_SIZE, Image.Resampling.LANCZOS)
                templates_set[file.stem.replace("attr_", "")] = img
            except Exception as e:
                print(f"加载套装模板 {file} 失败: {e}")

    return templates_phantom, templates_set


# 加载模板图像
templates_phantom, templates_set = load_template_images()


def diff_val(a, b):
    """计算绝对差值"""
    return np.abs(a.astype(int) - b.astype(int))


class ImageComparer:
    """图像比较器 - 直接比较两个图像"""

    @staticmethod
    def is_empty_icon(image, black_threshold=50, empty_percentage_threshold=80) -> bool:
        """
        检测图像是否为空（主要是黑色/透明）- 向量化版本
        image: PIL Image对象
        black_threshold: 黑色像素阈值
        empty_percentage_threshold: 空像素百分比阈值
        """
        if not isinstance(image, Image.Image):
            raise ValueError("需要PIL Image对象")

        # 确保图像是RGB或RGBA
        if image.mode == "P":
            image = image.convert("RGB")
        elif image.mode == "LA":
            image = image.convert("RGBA")

        img_array = np.array(image)

        # 获取图像尺寸和通道数
        height, width = img_array.shape[0], img_array.shape[1]

        # 根据图像模式确定通道数
        if len(img_array.shape) == 3:
            channels = img_array.shape[2]
        else:
            channels = 1

        # 向量化判断空像素
        if channels >= 3:
            # 处理RGB或RGBA图像
            rgb_channels = img_array[:, :, :3]
            if channels >= 4:
                alpha_channel = img_array[:, :, 3]
            else:
                alpha_channel = np.full((height, width), 255, dtype=img_array.dtype)

            # 判断黑色像素：RGB三通道都小于阈值
            is_black = np.all(rgb_channels < black_threshold, axis=2)

            # 判断透明像素：Alpha通道非常低
            is_transparent = alpha_channel < 10

            # 合并条件：黑色或透明都视为空像素
            is_empty = is_black | is_transparent

            # 计算空像素数量
            empty_pixel_count = np.sum(is_empty)
        else:
            # 处理灰度图像
            is_black = img_array < black_threshold
            empty_pixel_count = np.sum(is_black)

        total_pixels = height * width
        empty_percentage = (empty_pixel_count / total_pixels) * 100

        # 打印调试信息
        non_empty_count = total_pixels - empty_pixel_count
        logger.debug(
            f"空槽位检测: 非空像素={non_empty_count}/{total_pixels}, 空占比={empty_percentage:.1f}%"
        )

        # 如果空像素超过阈值，则视为空图标
        return empty_percentage > empty_percentage_threshold

    @staticmethod
    def compare_images(
        image1,
        image2,
        pixel_threshold=20,
        background_threshold=50,
        alpha_threshold=10,
        target_size=(32, 32),
    ) -> float:
        """
        比较两个图像
        image1, image2: PIL Image对象
        pixel_threshold: 像素差值阈值
        background_threshold: 背景阈值
        alpha_threshold: Alpha通道阈值
        target_size: 缩放目标大小 (width, height)
        """
        # 确保图像模式一致
        if image1.mode != image2.mode:
            # 如果有一个是RGBA，都转为RGBA
            if image1.mode == "RGBA" or image2.mode == "RGBA":
                image1 = image1.convert("RGBA")
                image2 = image2.convert("RGBA")
            else:
                # 否则转为RGB
                image1 = image1.convert("RGB")
                image2 = image2.convert("RGB")

        # 调整图像大小到目标尺寸
        if image1.size != target_size or image2.size != target_size:
            image1 = image1.resize(target_size, Image.Resampling.LANCZOS)
            image2 = image2.resize(target_size, Image.Resampling.LANCZOS)

        # 转换为numpy数组
        img1_array = np.array(image1)
        img2_array = np.array(image2)

        # 根据图像模式确定通道数
        if len(img1_array.shape) == 3:
            channels = img1_array.shape[2]
        else:
            channels = 1

        # 创建背景掩码（向量化操作）
        if channels >= 3:
            # RGB三通道图像
            if channels >= 4:
                # RGBA图像
                rgb1 = img1_array[:, :, :3]
                alpha1 = img1_array[:, :, 3]

                # 创建背景掩码：RGB都小于background_threshold 或 alpha < alpha_threshold
                background_mask = (
                    (rgb1[:, :, 0] < background_threshold)
                    & (rgb1[:, :, 1] < background_threshold)
                    & (rgb1[:, :, 2] < background_threshold)
                ) | (alpha1 < alpha_threshold)
            else:
                # RGB图像
                rgb1 = img1_array

                # 创建背景掩码：RGB都小于background_threshold
                background_mask = (
                    (rgb1[:, :, 0] < background_threshold)
                    & (rgb1[:, :, 1] < background_threshold)
                    & (rgb1[:, :, 2] < background_threshold)
                )
        else:
            # 灰度图像
            # 创建背景掩码：像素值小于background_threshold
            background_mask = img1_array < background_threshold

        # 反转掩码，获取非背景像素
        non_background_mask = ~background_mask

        # 如果没有非背景像素，返回0相似度
        if not np.any(non_background_mask):
            return 0.0

        # 计算相似像素（向量化操作）
        if channels >= 3:
            # 计算RGB通道差值
            if channels >= 4:
                rgb2 = img2_array[:, :, :3]
            else:
                rgb2 = img2_array

            # 计算每个通道的差值
            diff_r = diff_val(rgb1[:, :, 0], rgb2[:, :, 0])
            diff_g = diff_val(rgb1[:, :, 1], rgb2[:, :, 1])
            diff_b = diff_val(rgb1[:, :, 2], rgb2[:, :, 2])

            # 判断每个像素是否相似（所有通道差值都小于阈值）
            pixel_matches = (
                (diff_r < pixel_threshold)
                & (diff_g < pixel_threshold)
                & (diff_b < pixel_threshold)
            )
        else:
            # 灰度图像
            diff = diff_val(img1_array, img2_array)
            pixel_matches = diff < pixel_threshold

        # 只考虑非背景像素
        non_background_pixel_matches = pixel_matches & non_background_mask

        # 计算相似度
        similar_pixels = np.sum(non_background_pixel_matches)
        total_pixels = np.sum(non_background_mask)

        # 防止除零错误
        if total_pixels == 0:
            return 0.0

        # 返回相似度
        similarity = similar_pixels / total_pixels
        return float(similarity)

    @staticmethod
    def compare_echo_images(echo_image1, echo_image2) -> float:
        """比较声骸图像"""
        return ImageComparer.compare_images(
            echo_image1,
            echo_image2,
            pixel_threshold=20,  # 声骸像素差值阈值
            background_threshold=50,  # 声骸背景阈值
            alpha_threshold=10,  # 声骸Alpha阈值
            target_size=ECHO_SIZE,  # 声骸缩放大小
        )

    @staticmethod
    def compare_echo_set_images(set_image1, set_image2) -> float:
        """比较套装图像"""
        return ImageComparer.compare_images(
            set_image1,
            set_image2,
            pixel_threshold=25,  # 套装像素差值阈值
            background_threshold=50,  # 套装背景阈值
            alpha_threshold=10,  # 套装Alpha阈值
            target_size=SET_SIZE,  # 套装缩放大小
        )


async def batch_analyze_card_img(cropped_icons:list[Image.Image], i:str) -> dict[str, str | float]:
    """
    cropped_icons: 裁切出的声骸图像和套装图像
    """
    echo_icon = cropped_icons[0]  # 声骸图标
    set_icon = cropped_icons[1]  # 套装图标

    # 检查空槽位
    if ImageComparer.is_empty_icon(echo_icon) and ImageComparer.is_empty_icon(set_icon):
        return {
            "slot": i,
            "echo": "EMPTY",
            "echo_set": "EMPTY",
            "echo_confidence": 1.0,
            "set_confidence": 1.0,
        }

    # 识别套装
    set_match = "UNKNOWN"
    set_confidence = 0.0

    for name, template_img in templates_set.items():
        # 直接比较两个图像
        similarity = ImageComparer.compare_echo_set_images(set_icon, template_img)
        if similarity > set_confidence and similarity > 0.05:
            set_match = name
            set_confidence = similarity
            if similarity > 0.95:  # 高相似度直接确认
                break
    
    # 根据套装名获取对应的声骸ID列表，避免无效比较
    echo_ids_for_set = get_echo_ids_by_set_name(set_match)
    if not echo_ids_for_set:
        logger.warning(f"未找到套装 '{set_match}' 对应的声骸ID列表，使用全部声骸模板进行比较!")
        echo_ids_for_set = templates_phantom.keys()

    # 识别声骸
    echo_match = "UNKNOWN"
    echo_confidence = 0.0

    # for name, template_img in templates_phantom.items():
    for echo_id in echo_ids_for_set:
        name = str(echo_id)
        template_img = templates_phantom.get(name)
        # 直接比较两个图像
        similarity = ImageComparer.compare_echo_images(echo_icon, template_img)
        if similarity > echo_confidence and similarity > 0.05:
            echo_match = name
            echo_confidence = similarity
            if similarity > 0.95:  # 高相似度直接确认
                break

    return {
        "slot": i,
        "echo": echo_match,
        "echo_set": set_match,
        "echo_confidence": echo_confidence,
        "set_confidence": set_confidence,
    }
