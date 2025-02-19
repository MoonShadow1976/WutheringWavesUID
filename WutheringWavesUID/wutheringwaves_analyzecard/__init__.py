
from gsuid_core.bot import Bot
from gsuid_core.sv import SL, SV
from gsuid_core.models import Event
from gsuid_core.logger import logger

from .cardOCR import async_ocr, get_image, upload_discord_bot_card

 # 假设这是处理图片的函数

sv_discord_bot_card_analyze = SV(f"discord_bot卡片分析")


@sv_discord_bot_card_analyze.on_fullmatch(
    (
        f"分析卡片",
        f"卡片分析",
        f"dc卡片",
        f"识别卡片",
        f"分析",
    )
)
async def analyze_card(bot: Bot, ev: Event):
    """
    处理 Discord 上的图片分析请求。
    
    :param bot: Bot对象，用于发送消息。
    :param ev: 事件对象，包含用户信息和上传的图片信息。
    """

    resp = await bot.receive_resp(
        f'[鸣潮] 请发送dc官方bot生成的卡片图\n(分辨率尽可能为1920*1080，过低可能导致识别置信率降低)',
    )
    if resp is not None:
        await bot.send(f'分析中...')
        await async_ocr(bot, resp)