from io import BytesIO

from gsuid_core.logger import logger
from gsuid_core.utils.image.convert import convert_img
import httpx
from PIL import Image

from ..utils.resource.download_github import check_speed


async def fetch_image(client: httpx.AsyncClient, url: str) -> bytes | None:
    """异步获取图片数据"""
    try:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except (httpx.HTTPError, OSError) as e:
        logger.error(f"获取图片失败: {type(e).__name__} - {e}")
        return None


async def draw_offical_calendar_img() -> bytes | str:
    """生成官方日历图片（复用 check_speed 选择 GitHub 镜像站）"""
    try:
        tag, base_url = await check_speed()
        url = f"{base_url.rstrip('/')}/images/calendar.jpg"
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            logger.info(f"[官方日历] 使用镜像: {tag} -> {url}")
            if image_data := await fetch_image(client, url):
                try:
                    img = Image.open(BytesIO(image_data))
                    return await convert_img(img)
                except Exception as e:
                    logger.error(f"图片处理失败: {e}")
                    return f"图片处理失败: {e}"
    except Exception as e:
        logger.exception(f"[官方日历] 获取资源失败: {e}")

    return "所有镜像源均不可用，请检查网络"
