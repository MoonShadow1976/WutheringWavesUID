from typing import Any

from gsuid_core.logger import logger
import httpx

from ..api.wwapi import (
    UPLOAD_ABYSS_RECORD_URL,
    UPLOAD_GACHA_RECORD_URL,
    UPLOAD_SLASH_RECORD_URL,
    UPLOAD_URL,
)
from ..database.models import WavesUserAvatar
from .const import QUEUE_ABYSS_RECORD, QUEUE_GACHA_RECORD, QUEUE_SCORE_RANK, QUEUE_SLASH_RECORD
from .queues import event_handler, start_dispatcher


async def concatenate_user_id_for_avatar(item: dict) -> dict:
    """拼接用户id与获取头像有关的字符串 - 头像hash"""
    if "user_id" in item:
        qid = item["user_id"]
        logger.debug(f"[鸣潮][总排行上传] 用户id: {qid}")
        data = await WavesUserAvatar.select_data(qid)
        if data:
            logger.debug(f"[鸣潮][总排行上传] 用户别名hash: {data}")
            if data.bot_id in ["qqgroup", "qq_official"]:
                appid = data.avatar_hash
                item["user_id"] = f"{appid}/{qid}"
            elif data.bot_id in ["discord"]:
                avatar_hash = data.avatar_hash
                item["user_id"] = f"{qid}/{avatar_hash}"
            else:
                logger.warning(f"[鸣潮][总排行上传] 用户别名处理不支持的 bot_id: {data.bot_id}")

    return item


@event_handler(QUEUE_SCORE_RANK)
async def send_score_rank(item: Any):
    if not item:
        return
    if not isinstance(item, dict):
        return
    from ...wutheringwaves_config import WutheringWavesConfig

    WavesToken = WutheringWavesConfig.get_config("WavesToken").data

    if not WavesToken:
        return

    item = await concatenate_user_id_for_avatar(item)
    logger.debug(f"[鸣潮][总排行上传] item: {item}")

    async with httpx.AsyncClient() as client:
        res = None
        try:
            res = await client.post(
                UPLOAD_URL,
                json=item,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {WavesToken}",
                },
                timeout=httpx.Timeout(10),
            )
            logger.info(f"上传面板结果: {res.status_code} - {res.text}")
        except Exception as e:
            logger.exception(f"上传面板失败: {res.text if res else ''} {e}")


@event_handler(QUEUE_ABYSS_RECORD)
async def send_abyss_record(item: Any):
    if not item:
        return
    if not isinstance(item, dict):
        return
    from ...wutheringwaves_config import WutheringWavesConfig

    WavesToken = WutheringWavesConfig.get_config("WavesToken").data

    if not WavesToken:
        return

    item = await concatenate_user_id_for_avatar(item)

    async with httpx.AsyncClient() as client:
        res = None
        try:
            res = await client.post(
                UPLOAD_ABYSS_RECORD_URL,
                json=item,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {WavesToken}",
                },
                timeout=httpx.Timeout(10),
            )
            logger.info(f"上传深渊结果: {res.status_code} - {res.text}")
        except Exception as e:
            logger.exception(f"上传深渊失败: {res.text if res else ''} {e}")


@event_handler(QUEUE_SLASH_RECORD)
async def send_slash_record(item: Any):
    if not item:
        return
    if not isinstance(item, dict):
        return
    from ...wutheringwaves_config import WutheringWavesConfig

    WavesToken = WutheringWavesConfig.get_config("WavesToken").data

    if not WavesToken:
        return

    item = await concatenate_user_id_for_avatar(item)

    async with httpx.AsyncClient() as client:
        res = None
        try:
            res = await client.post(
                UPLOAD_SLASH_RECORD_URL,
                json=item,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {WavesToken}",
                },
                timeout=httpx.Timeout(10),
            )
            logger.info(f"上传冥海结果: {res.status_code} - {res.text}")
        except Exception as e:
            logger.exception(f"上传冥海失败: {res.text if res else ''} {e}")


@event_handler(QUEUE_GACHA_RECORD)
async def send_gacha_record(item: Any):
    if not item:
        return
    if not isinstance(item, dict):
        return
    from ...wutheringwaves_config import WutheringWavesConfig

    WavesToken = WutheringWavesConfig.get_config("WavesToken").data

    if not WavesToken:
        return

    item = await concatenate_user_id_for_avatar(item)

    async with httpx.AsyncClient() as client:
        res = None
        try:
            res = await client.post(
                UPLOAD_GACHA_RECORD_URL,
                json=item,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {WavesToken}",
                },
                timeout=httpx.Timeout(10),
            )
            logger.info(f"上传抽卡记录结果: {res.status_code} - {res.text}")
        except Exception as e:
            logger.exception(f"上传抽卡记录失败: {res.text if res else ''} {e}")


def init_queues():
    # 启动任务分发器
    start_dispatcher(daemon=True)
