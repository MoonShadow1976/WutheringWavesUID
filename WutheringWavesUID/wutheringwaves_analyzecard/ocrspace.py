# 标准库
import asyncio
import base64
from io import BytesIO
import re
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
OCR_TIMEOUT = 60  # 访问超时
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


async def _get_status_page_id_by_custom_domain() -> int | None:
    """通过自定义域名获取 Checkly Status Page ID"""
    metadata_url = "https://api.checklyhq.com/v1/status-page/status.ocr.space/metadata?type=customDomain"
    try:
        session = await get_global_session()
        async with session.get(metadata_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning(f"[鸣潮][OCRspace Checkly] 获取元数据失败，HTTP {resp.status}")
                return None
            data = await resp.json()
            return data.get("id")
    except Exception as e:
        logger.warning(f"[鸣潮][OCRspace Checkly] 获取 Status Page ID 异常: {e}")
        return None


async def check_ocr_engine_accessible(plan: str) -> int:
    """
    通过 Checkly API 检查指定套餐（FREE 或 PRO）的 OCR 引擎健康状况。
    优先返回可用引擎：2 > 1 > 其他引擎

    参数:
        plan: "FREE" 或 "PRO"

    返回:
        正数: 可用引擎编号（2/1/3...）
        0: 无可用引擎
        -1: 网络请求失败或解析异常
    """
    # 动态获取 Status Page ID
    status_page_id = await _get_status_page_id_by_custom_domain()
    if status_page_id is None:
        logger.warning("[鸣潮][OCRspace Checkly] 无法获取 Status Page ID，使用备用 ID（746345）")
        status_page_id = 746345  # 备用 ID

    url = f"https://api.checklyhq.com/v1/status-page/{status_page_id}/statuses?page=1&limit=15"

    try:
        session = await get_global_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                logger.warning(f"[鸣潮][OCRspace Checkly] API 返回非 200: {resp.status}")
                return -1
            data = await resp.json()
            results = data.get("results", [])

            # 根据套餐匹配检查项名称
            plan_upper = plan.upper()
            if plan_upper == "FREE":
                pattern = re.compile(r"Free - Engine(\d+)", re.IGNORECASE)
            elif plan_upper == "PRO":
                pattern = re.compile(r"PRO\d?\s*\-?\s*Engine(\d+)", re.IGNORECASE)
            else:
                logger.warning(f"[鸣潮][OCRspace Checkly] 不支持的套餐类型: {plan}")
                return -1

            engine_status = []
            for item in results:
                name = item.get("name", "")
                if not item.get("activated", True):
                    continue
                match = pattern.search(name)
                if match:
                    engine_num = int(match.group(1))
                    has_failures = item.get("status", {}).get("hasFailures", True)
                    is_up = not has_failures
                    engine_status.append((engine_num, is_up))

            if not engine_status:
                logger.warning(f"[鸣潮][OCRspace Checkly] 未找到 {plan} 套餐的任何引擎")
                return 0

            # 优先级：引擎2 > 引擎1 > 其他引擎
            def priority(engine_num: int) -> int:
                if engine_num == 2:
                    return 0
                elif engine_num == 1:
                    return 1
                else:
                    return 2 + engine_num

            engine_status.sort(key=lambda x: priority(x[0]))

            logger.info(f"[鸣潮][OCRspace Checkly] {plan} 套餐引擎状态: {engine_status}")
            for engine_num, is_up in engine_status:
                if is_up:
                    logger.info(f"[鸣潮]使用OCR.space服务engine：{engine_num}")
                    return engine_num

            logger.warning(f"[鸣潮][OCRspace Checkly] {plan} 套餐所有引擎均不可用")
            return 0

    except Exception as e:
        logger.warning(f"[鸣潮][OCRspace Checkly] 请求异常: {e}")
        return -1


async def ocrspace(
    cropped_images: list[Image.Image],
    bot: Bot,
    at_sender: bool,
    language: str = "cht",
    isTable: bool = True,
    need_all_pass: bool = False,
) -> list | str:
    """
    异步OCR识别函数
    """
    api_key_list = WutheringWavesConfig.get_config("OCRspaceApiKeyList").data  # 从控制台获取OCR.space的API密钥
    if api_key_list == []:
        logger.warning("[鸣潮] OCRspace API密钥为空！请检查控制台。")
        return "[鸣潮] OCRspace API密钥未配置，请检查控制台。\n"

    # 初始化密钥和引擎
    API_KEY = None
    NEGINE_NUM = None

    # 遍历密钥
    ocr_results = None
    for key in api_key_list:
        if not key:
            continue

        API_KEY = key

        # 检查可用引擎
        if key[0] != "K":
            NEGINE_NUM = await check_ocr_engine_accessible("PRO")  # 激活PRO计划
        else:
            NEGINE_NUM = await check_ocr_engine_accessible("FREE")

        if NEGINE_NUM == 1 and API_KEY == api_key_list[0]:
            await bot.send("[鸣潮] 当前OCR服务器识别准确率不高，可能会导致识别失败，请考虑稍后使用。\n", at_sender)
        elif NEGINE_NUM == 0:
            return "[鸣潮] OCR服务暂时不可用，请稍后再试。\n"
        elif NEGINE_NUM == -1:
            return "[鸣潮] 服务器访问OCR服务失败，请检查服务器网络状态。\n"

        ocr_results = await images_ocrspace(API_KEY, NEGINE_NUM, cropped_images, language=language, isTable=isTable)
        logger.info(f"[鸣潮][OCRspace]dc卡片识别数据: {ocr_results}")
        if ocr_results:
            if need_all_pass:
                if all(result.get("error") is None for result in ocr_results):
                    logger.success("[鸣潮]OCRspace 识别成功！")
                    break
            else:
                if any(result.get("error") is None for result in ocr_results):
                    logger.success("[鸣潮]OCRspace 识别成功！")
                    break

    if API_KEY is None:
        return "[鸣潮] OCRspace API密钥不可用！请等待额度恢复或更换密钥\n"

    error_msg = "[鸣潮]OCRspace识别失败！或是输入异常或是OCR服务故障，请尝试修改输入或等待OCR服务恢复\n"
    if not ocr_results:
        logger.warning(error_msg)
        return error_msg
    if need_all_pass:
        if not all(result.get("error") is None for result in ocr_results):
            logger.warning(error_msg)
            return error_msg
    else:
        if not any(result.get("error") is None for result in ocr_results):
            logger.warning(error_msg)
            return error_msg

    return ocr_results


async def images_ocrspace(api_key, engine_num, cropped_images, language="cht", isTable=True):
    """
    使用 OCR.space 免费API识别碎块图片
    """
    API_KEY = api_key
    FREE_URL = "https://api.ocr.space/parse/image"
    PRO_URL = "https://apipro2.ocr.space/parse/image"
    if API_KEY[0] != "K":
        API_URL = PRO_URL
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
            "language": language,
            "isOverlayRequired": False,
            "base64Image": f"data:image/png;base64,{img_base64}",
            "OCREngine": ENGINE_NUM,
            "isTable": isTable,
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
        async with session.post(url, data=payload, timeout=OCR_TIMEOUT) as response:  # ✅ 添加单次请求超时
            # 检查HTTP状态码
            if response.status != 200:
                # 修改错误返回格式为字典（与其他成功结果结构一致）
                return [{"error": f"HTTP Error {response}", "text": None}]

            data = await response.json()
            logger.debug(f"[鸣潮]OCR.space 返回结果：{data}")

            # 解析结果
            if not data.get("ParsedResults"):
                if data.get("ErrorDetails"):
                    return [{"error": f"{data['ErrorDetails']}", "text": None}]
                return [{"error": "No Results", "text": None}]

            # 提取识别结果
            for result in data.get("ParsedResults", []):
                # 补充完整文本
                if result.get("ParsedText"):
                    return [{"error": None, "text": result.get("ParsedText")}]

            return [{"error": None, "text": None}]
    except asyncio.TimeoutError:
        logger.warning(f"[鸣潮] OCR.space 请求超时({OCR_TIMEOUT}秒)")
        return [{"error": f"Request Timeout: {OCR_TIMEOUT} seconds", "text": None}]
    except Exception as e:
        logger.warning(f"[鸣潮] OCR.space 请求异常: {e}")
        return [{"error": f"Processing Error: {e}", "text": None}]


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
            url_cut = re.split(r"(https?://)", " ".join(urls))[1:]  # 拆分连续的URL
            url_list = [url_cut[i] + url_cut[i + 1].strip() for i in range(0, len(url_cut), 2)]
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
