from datetime import datetime
import hashlib
import json
import time

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV
import httpx

from ..utils.resource.download_github import check_speed

sv_waves_code = SV("鸣潮兑换码")

invalid_code_list = ("MINGCHAO",)

# 国服接口配置（带签名）
api_path = "dhmCode/index"
tool_id = "10"
sign_key = "38d8cb06671bef65"
url = f"https://huodong2.4399.com/n/comm/tool/api.php?path={api_path}&tool_id={tool_id}"


def is_code_expired(etime: str) -> bool:
    """检查国服兑换码是否已过期"""
    if not etime:
        return False

    try:
        # 新接口的etime格式: "2026-06-01 00:00:00"
        expire_date = datetime.strptime(etime, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        return now > expire_date
    except Exception:
        return False


@sv_waves_code.on_fullmatch(("code", "兑换码"))
async def get_sign_func(bot: Bot, ev: Event):
    # 分别获取结果
    list1 = await get_code_list()  # 国服（已修复签名）
    list2 = await get_oversea_code_list()  # 国际服

    msgs = []
    msgs.append("（前瞻兑换码互通都可使用）")

    # 处理国服兑换码
    if list1 is not None:
        for code in list1:
            order = code.get("code", "")
            if order in invalid_code_list or not order:
                continue
            reward = code.get("content", "")
            label = code.get("description", "")
            etime = code.get("etime", "")
            if is_code_expired(etime):
                continue

            if order == "MINGCHAO666":
                label += "国服专属长期兑换码"

            msg = [f"兑换码: {order}", f"奖励: {reward}", label]
            msgs.append("\n".join(msg))

    # 处理国际服兑换码
    if list2 is not None:
        for code in list2:
            is_fail = code.get("is_fail", "0")
            if is_fail == "1":
                continue
            order = code.get("order", "")
            if order in invalid_code_list or not order:
                continue
            reward = code.get("reward", "")
            label = code.get("label", "")
            etime = code.get("over_time", "")
            if is_code_expired(etime):
                continue

            msg = [f"兑换码: {order}", f"奖励: {reward}", label]
            msgs.append("\n".join(msg))

    if len(msgs) <= 1:  # 只有开头提示，没有有效兑换码
        return await bot.send("[获取兑换码失败] 没有找到有效的兑换码或均已过期")

    await bot.send("\n\n".join(msgs))


async def get_code_list():
    """获取国服兑换码（带签名验证）"""
    try:
        timestamp = int(time.time())
        sign_content = f"scookiet{timestamp}tool_id{tool_id}path{api_path}{sign_key}"
        token = hashlib.md5(sign_content.encode(), usedforsecurity=False).hexdigest()
        params = {
            "child_id": "11",
            "keyword": "",
            "status": "1",  # 只查询有效的兑换码
            "currentPage": "1",
            "pageSize": "20",
            "scookie": "",
            "device": "",
            "t": str(timestamp),
        }
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.post(
                url,
                data=params,
                headers={"X-Token": token},
                timeout=10,
            )
            res.raise_for_status()
            json_data = res.json()
            logger.debug(f"[获取兑换码-国服] url:{url}, codeList:{json_data}")
            if json_data.get("success"):
                return json_data.get("list", [])
            logger.warning(f"[获取兑换码-国服] 失败 error_code:{json_data.get('error_code')}, msg:{json_data.get('msg')}")
            return []
    except Exception as e:
        logger.exception("[获取兑换码-国服] 异常 ", e)
        return []


async def get_oversea_code_list():
    """获取国际服兑换码（复用 check_speed 选择 GitHub 镜像站）"""
    try:
        _tag, base_url = await check_speed()
        url = f"{base_url.rstrip('/')}/js/oversea_codes.js"
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            res = await client.get(url, timeout=10)
            if res.status_code != 200:
                logger.error(f"[获取兑换码-国际服] 无效响应 {res.status_code}: {url}")
                return []
            content = res.text
    except Exception as e:
        logger.exception(f"[获取兑换码-国际服] 请求失败: {e}")
        return []

    try:
        # oversea_codes.js 格式: var mlList = [...];
        json_data = content.split("=", 1)[1].strip().rstrip(";")
        logger.debug(f"[获取兑换码-国际服] codeList:{json_data}")
        return json.loads(json_data)
    except (IndexError, json.JSONDecodeError) as e:
        logger.exception(f"[获取兑换码-国际服] 解析文件失败: {e}")
        return []
