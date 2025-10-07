import json
import re
import time
from datetime import datetime

import httpx

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

sv_waves_code = SV("鸣潮兑换码")

invalid_code_list = ("MINGCHAO",)

url = "https://newsimg.5054399.com/comm/mlcxqcommon/static/wap/js/data_102.js?{}&callback=?&_={}"


@sv_waves_code.on_fullmatch((f"code", f"兑换码"))
async def get_sign_func(bot: Bot, ev: Event):
    # 分别获取结果
    list1 = await get_code_list()  # 可能返回列表或None
    list2 = await get_oversea_code_list()  # 可能返回列表或None

    # 安全合并
    code_list = []
    if list1 is not None:
        code_list.extend(list1)
    if list2 is not None:
        code_list.extend(list2)
    if not code_list:
        return await bot.send("[获取兑换码失败] 请稍后再试")

    msgs = []
    msgs.append("国际服只能使用已标注的兑换码（前瞻兑换码互通都可使用）")
    for code in code_list:
        is_fail = code.get("is_fail", "0")
        if is_fail == "1":
            continue
        order = code.get("order", "")
        if order in invalid_code_list or not order:
            continue
        reward = code.get("reward", "")
        label = code.get("label", "")
        msg = [f"兑换码: {order}", f"奖励: {reward}", label]
        msgs.append("\n".join(msg))

    await bot.send(msgs)


async def get_code_list():
    try:
        now = datetime.now()
        time_string = f"{now.year - 1900}{now.month - 1}{now.day}{now.hour}{now.minute}"
        now_time = int(time.time() * 1000)
        new_url = url.format(time_string, now_time)
        async with httpx.AsyncClient(timeout=None) as client:
            res = await client.get(new_url, timeout=10)
            json_data = res.text.split("=", 1)[1].strip().rstrip(";")
            logger.debug(f"[获取兑换码] url:{new_url}, codeList:{json_data}")
            return json.loads(json_data)

    except Exception as e:
        logger.exception("[获取兑换码失败] ", e)
        return

async def get_oversea_code_list():
    code_url = "https://cdn.jsdelivr.net/gh/MoonShadow1976/WutheringWaves_OverSea_StaticAssets@main/js/oversea_codes.js"
        
    # 备选CDN镜像源
    mirrors = [
        code_url,
        code_url.replace("cdn.jsdelivr.net", "fastly.jsdelivr.net"),
        code_url.replace("cdn.jsdelivr.net", "gcore.jsdelivr.net"),
        "https://raw.githubusercontent.com/MoonShadow1976/WutheringWaves_OverSea_StaticAssets/main/js/oversea_codes.js"
    ]

    for url in mirrors:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                res = await client.get(url, timeout=10)

                if res.status_code != 200:
                    logger.error(f"[获取兑换码-国际服] 无效响应 {res.status_code}: {url}")
                    continue

                json_data = res.text.split("=", 1)[1].strip().rstrip(";")
                logger.debug(f"[获取兑换码-国际服] url:{url}, codeList:{json_data}")
                return json.loads(json_data)
        except Exception as e:
            logger.error(f"[获取兑换码-国际服] 请求失败 {url}: {str(e)}")

    logger.error("[获取兑换码-国际服] 所有镜像源均失败")
    return [{"order": "国际服兑换码获取失败,请检查服务器网络"}]


def is_code_expired(label: str) -> bool:
    if not label:
        return False

    # 使用正则提取月份和日期
    pattern = r"(\d{1,2})月(\d{1,2})日(\d{1,2})点"
    match = re.search(pattern, label)
    if not match:
        return False

    expire_month = int(match.group(1))
    expire_day = int(match.group(2))
    expire_hour = int(match.group(2))

    now = datetime.now()
    current_month = now.month

    expire_year = now.year
    # 处理跨年的情况
    if current_month < expire_month:
        # 当前月份小于截止月份，说明截止日期是去年的
        expire_year -= 1
    elif current_month == expire_month:
        # 当前月份等于截止月份，需要比较日期
        if now.day > expire_day:
            # 当前日期已经过了截止日期，说明是明年的
            expire_year += 1
    else:
        # 当前月份大于截止月份，使用当前年份
        pass

    if expire_hour == 24:
        expire_hour = 23
        expire_min = 59
        expire_sec = 59
    else:
        expire_min = 0
        expire_sec = 0

    # 构建截止时间
    expire_date = datetime(
        expire_year, expire_month, expire_day, expire_hour, expire_min, expire_sec
    )

    # 比较时间
    return now > expire_date
