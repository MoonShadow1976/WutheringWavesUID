from io import BytesIO
from typing import Union

import httpx
from PIL import Image
from gsuid_core.logger import logger
from gsuid_core.utils.image.convert import convert_img

# 创建全局异步客户端（保持连接复用）
client = httpx.AsyncClient()

async def fetch_image(url: str) -> Union[bytes, None]:
    """异步获取图片数据"""
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        return resp.content
    except (httpx.HTTPError, OSError) as e:
        logger.error(f"获取图片失败: {type(e).__name__} - {e}")
        return None

async def draw_offical_calendar_img() -> Union[bytes, str]:
    """生成官方日历图片"""
    calendar_url = "https://cdn.jsdelivr.net/gh/MoonShadow1976/WutheringWaves_OverSea_StaticAssets@latest/images/calendar.jpg"
    
    # 备选CDN镜像源
    mirrors = [
        calendar_url,
        calendar_url.replace("cdn.jsdelivr.net", "fastly.jsdelivr.net"),
        calendar_url.replace("cdn.jsdelivr.net", "gcore.jsdelivr.net"),
        "https://raw.githubusercontent.com/MoonShadow1976/WutheringWaves_OverSea_StaticAssets/main/images/calendar.jpg"
    ]
    
    for url in mirrors:
        if image_data := await fetch_image(url):
            try:
                img = Image.open(BytesIO(image_data))
                return await convert_img(img)
            except Exception as e:
                logger.error(f"图片处理失败: {e}")

    
    return "所有镜像源均不可用，请检查网络"
