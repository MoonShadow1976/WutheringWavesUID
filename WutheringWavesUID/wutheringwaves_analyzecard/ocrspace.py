# 标准库
import asyncio
import base64
from io import BytesIO
import ssl

import aiohttp
from aiohttp import ClientTimeout

# 项目内部模块
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
import httpx
from PIL import Image

from ..wutheringwaves_config import WutheringWavesConfig

# 全局配置
OCR_TIMEOUT = ClientTimeout(total=10)  # 总超时 10 秒
OCR_SESSION = None  # 全局会话实例


async def get_global_session():
    global OCR_SESSION
    if OCR_SESSION is None or OCR_SESSION.closed:
        # 设置连接池参数：最多 10 个连接，空闲 60 秒自动关闭
        connector = aiohttp.TCPConnector(
            limit=10,
            keepalive_timeout=60,  # 空闲连接保留 60 秒
        )
        OCR_SESSION = aiohttp.ClientSession(connector=connector, timeout=ClientTimeout(total=10))
        logger.info("[鸣潮]已创建新的全局 OCR 会话")
    return OCR_SESSION


async def check_ocr_link_accessible(key="helloworld") -> bool:
    """
    检查OCR.space示例链接是否能正常访问，返回布尔值。
    """
    url = "https://api.ocr.space/parse/imageurl"
    payload = {
        "url": "https://dl.a9t9.com/ocr/solarcell.jpg",
        "apikey": f"{key}",
    }
    try:
        session = await get_global_session()  # 复用全局会话
        async with session.get(url, data=payload, timeout=ClientTimeout(total=10)) as response:
            data = await response.json()
            logger.debug(f"[鸣潮]OCR.space示例链接访问成功，状态码为 {response.status}\n内容：{data}")
            return response.status == 200
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.warning("[鸣潮]OCR.space 访问示例链接失败，请检查网络或服务状态。")
        return False


async def check_ocr_engine_accessible() -> int:
    """
    检查OcrEngine_2状态（通过解析HTML表格）
    返回1表示UP，0表示DOWN或其他错误
    """
    from bs4 import BeautifulSoup

    url = "https://status.ocr.space"
    try:
        session = await get_global_session()
        async with session.get(url, timeout=ClientTimeout(total=10)) as response:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # 定位目标表格
            target_table = soup.find("h4", string="API Access Points").find_next("table")

            # 查找包含"Free OCR API"的行
            for row in target_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 4 and "Free OCR API" in cells[0].text:
                    status_1 = cells[2].text.strip().upper()
                    status_2 = cells[3].text.strip().upper()
                    logger.info(f"[鸣潮] OcrEngine_1:{status_1}, OcrEngine_2:{status_2}")
                    if status_2 == "UP":
                        return 2
                    elif status_1 == "UP":
                        return 1
                    else:
                        return 0

            logger.warning("[鸣潮] 未找到状态行")
            return 1

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning(f"[鸣潮] 网络错误: {e}")
        return -1
    except Exception as e:
        logger.warning(f"[鸣潮] 解析异常: {e}")
        return -1


async def ocrspace(cropped_images: list[Image.Image], bot: Bot, at_sender: bool) -> list | str:
    """
    异步OCR识别函数
    """
    api_key_list = WutheringWavesConfig.get_config("OCRspaceApiKeyList").data  # 从控制台获取OCR.space的API密钥
    if api_key_list == []:
        logger.warning("[鸣潮] OCRspace API密钥为空！请检查控制台。")
        return "[鸣潮] OCRspace API密钥未配置，请检查控制台。\n"

    # 检查可用引擎
    engine_num = await check_ocr_engine_accessible()
    logger.info(f"[鸣潮]OCR.space服务engine：{engine_num}")
    # 初始化密钥和引擎
    API_KEY = None
    NEGINE_NUM = None

    # 遍历密钥
    ocr_results = None
    for key in api_key_list:
        if not key:
            continue

        API_KEY = key
        NEGINE_NUM = engine_num
        if key[0] != "K":
            NEGINE_NUM = 3  # 激活PRO计划

        if NEGINE_NUM == 1 and API_KEY == api_key_list[0]:
            await bot.send("[鸣潮] 当前OCR服务器识别准确率不高，可能会导致识别失败，请考虑稍后使用。\n", at_sender)
        elif NEGINE_NUM == 0:
            return "[鸣潮] OCR服务暂时不可用，请稍后再试。\n"
        elif NEGINE_NUM == -1:
            return "[鸣潮] 服务器访问OCR服务失败，请检查服务器网络状态。\n"

        ocr_results = await images_ocrspace(API_KEY, NEGINE_NUM, cropped_images)
        logger.info(f"[鸣潮][OCRspace]dc卡片识别数据:\n{ocr_results}")
        if not ocr_results[0]["error"]:
            logger.success("[鸣潮]OCRspace 识别成功！")
            break

    if API_KEY is None:
        return "[鸣潮] OCRspace API密钥不可用！请等待额度恢复或更换密钥\n"

    if not ocr_results or ocr_results[0]["error"]:
        logger.warning("[鸣潮]OCRspace识别失败！请检查服务器网络是否正常。")
        return "[鸣潮]OCRspace识别失败！请检查服务器网络是否正常。\n"

    return ocr_results


async def images_ocrspace(api_key, engine_num, cropped_images):
    """
    使用 OCR.space 免费API识别碎块图片
    """
    API_KEY = api_key
    FREE_URL = "https://api.ocr.space/parse/image"
    PRO_URL = "https://apipro2.ocr.space/parse/image"
    if engine_num == 3:
        API_URL = PRO_URL
        ENGINE_NUM = 2
    else:
        API_URL = FREE_URL
        ENGINE_NUM = engine_num
    logger.info(f"[鸣潮]使用 {API_URL} 识别图片")

    session = await get_global_session()  # 复用全局会话
    tasks = []
    payloads = []  # 存储所有payload
    for img in cropped_images:
        # 将PIL.Image转换为base64
        try:
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            logger.warning(f"图像转换错误: {e}")
            continue

        # 构建请求参数
        """
        language: 仅繁体中文（正确参数值）
        isOverlayRequired: 需要坐标信息
        OCREngine: 使用引擎2, 识别效果更好，声骸识别差一些
        isTable: 启用表格识别模式
        detectOrientation: 自动检测方向
        scale: 图像缩放增强
        """
        payload = {
            "apikey": API_KEY,
            "language": "cht",
            "isOverlayRequired": False,
            "base64Image": f"data:image/png;base64,{img_base64}",
            "OCREngine": ENGINE_NUM,
            "isTable": True,
            "detectOrientation": False,
            "scale": False,
        }
        payloads.append(payload)

    # 添加0.1秒固定延迟的请求函数
    async def delayed_fetch(payload):
        await asyncio.sleep(0.5)  # 固定0.5秒延迟
        return await fetch_ocr_result(session, API_URL, payload)

    # 创建所有任务
    tasks = [delayed_fetch(payload) for payload in payloads]

    # 限制并发数为1防止超过API限制
    semaphore = asyncio.Semaphore(1)
    # 修改返回结果处理
    results = await asyncio.gather(*(process_with_semaphore(task, semaphore) for task in tasks))

    # 扁平化处理（合并所有子列表）
    return [item for sublist in results for item in sublist]


async def process_with_semaphore(task, semaphore):
    async with semaphore:
        return await task


async def fetch_ocr_result(session, url, payload):
    """发送OCR请求并处理响应"""
    try:
        async with session.post(url, data=payload, timeout=10) as response:  # ✅ 添加单次请求超时
            # 检查HTTP状态码
            if response.status != 200:
                # 修改错误返回格式为字典（与其他成功结果结构一致）
                return [{"error": f"HTTP Error {response}", "text": None}]

            data = await response.json()

            # 解析结果
            if not data.get("ParsedResults"):
                return [{"error": "No Results", "text": None}]

            # 提取识别结果
            for result in data.get("ParsedResults", []):
                # 补充完整文本
                if result.get("ParsedText"):
                    return [{"error": None, "text": result.get("ParsedText")}]

            return [{"error": "No Results", "text": None}]

    except Exception as e:
        return [{"error": f"Processing Error:{e}", "text": None}]


async def get_image(ev: Event):
    """
    获取图片链接
    change from .upload_card.get_image
    """
    res = []
    for content in ev.content:
        if content.type == "img" and content.data and isinstance(content.data, str) and content.data.startswith("http"):
            res.append(content.data)
        elif content.type == "image" and content.data and isinstance(content.data, str) and content.data.startswith("http"):
            res.append(content.data)
        elif (
            content.type == "image"
            and content.data
            and isinstance(content.data, dict)
            and content.data.get("url")
            and content.data["url"].startswith("http")
        ):  # discord attachment 类
            res.append(content.data["url"])
        elif content.type == "text" and content.data and isinstance(content.data, str):
            import re
            urls = re.findall(r'https?://[^\s<>"\'()（）]+', content.data)  # 从文本中提取所有HTTP/HTTPS链接
            url_cut = re.split(r'(https?://)', ' '.join(urls))[1:]  # 拆分连续的URL
            url_list = [url_cut[i] + url_cut[i+1].strip() for i in range(0, len(url_cut), 2)]
            res.extend(url_list)

    if not res and ev.image:
        res.append(ev.image)

    logger.debug(f"[鸣潮]获取图片res: {res}")
    return res


async def get_upload_img(ev: Event):
    """
    获取上传给机器人的图片
    change from .upload_card.upload_custom_card
    """
    upload_images = await get_image(ev)
    if not upload_images:
        return False, None

    success = False
    images = []
    for url in upload_images:
        if not url:
            continue
        logger.info(f"[鸣潮]卡片分析上传链接：{url}")

        if httpx.__version__ >= "0.28.0":
            ssl_context = ssl.create_default_context()
            # ssl_context.set_ciphers("AES128-GCM-SHA256")
            ssl_context.set_ciphers("DEFAULT")
            sess = httpx.AsyncClient(verify=ssl_context)
        else:
            sess = httpx.AsyncClient()

        try:
            if isinstance(sess, httpx.AsyncClient):
                res = await sess.get(url)
                image_data = res.read()
                retcode = res.status_code
            else:
                async with sess.get(url) as resp:
                    image_data = await resp.read()
                    retcode = resp.status

            if retcode == 200:
                images.append(Image.open(BytesIO(image_data)))
                success = True
                logger.success("[鸣潮]图片获取完成！")
            else:
                logger.warning(f"[鸣潮]图片获取失败！错误码{retcode}")

        except Exception as e:
            logger.error(e)
            logger.warning("[鸣潮]图片获取失败！")

    if success:
        return True, images
    else:
        return False, None
