import asyncio
import hashlib
import re
import uuid
from pathlib import Path
from typing import Optional, Union

import httpx
from async_timeout import timeout
from pydantic import BaseModel
from starlette.responses import HTMLResponse

from gsuid_core.bot import Bot
from gsuid_core.config import core_config
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from gsuid_core.utils.cookie_manager.qrlogin import get_qrcode_base64
from gsuid_core.web_app import app

from ..utils.cache import TimedCache
from ..utils.database.models import WavesBind, WavesUser
from ..utils.resource.RESOURCE_PATH import waves_templates
from ..utils.util import get_public_ip
from ..utils.waves_api import waves_api
from ..wutheringwaves_config import PREFIX, WutheringWavesConfig
from ..wutheringwaves_user import deal
from ..wutheringwaves_user.login_succ import login_success_msg

cache = TimedCache(timeout=600, maxsize=10)

game_title = "[鸣潮]"
msg_error = "[鸣潮] 登录失败\n1.是否注册过库街区\n2.库街区能否查询当前鸣潮特征码数据\n"


class LoginModel(BaseModel):
    auth: str
    mobile: str
    code: str


class InternationalLoginModel(BaseModel):
    auth: str
    email: str
    password: str
    geetest_data: Optional[str] = None  # Geetest 驗證數據


async def get_url() -> tuple[str, bool]:
    url = WutheringWavesConfig.get_config("WavesLoginUrl").data
    if url:
        if not url.startswith("http"):
            url = f"https://{url}"
        return url, WutheringWavesConfig.get_config("WavesLoginUrlSelf").data
    else:
        HOST = core_config.get_config("HOST")
        PORT = core_config.get_config("PORT")

        if HOST == "localhost" or HOST == "127.0.0.1":
            _host = "localhost"
        else:
            _host = await get_public_ip(HOST)

        return f"http://{_host}:{PORT}", True


def is_valid_chinese_phone_number(phone_number):
    # 正则表达式匹配中国大陆的手机号
    pattern = re.compile(r"^1[3-9]\d{9}$")
    return pattern.match(phone_number) is not None


def is_validate_code(code):
    # 正则表达式匹配6位数字
    pattern = re.compile(r"^\d{6}$")
    return pattern.match(code) is not None


def get_token(userId: str):
    return hashlib.sha256(userId.encode()).hexdigest()[:8]


async def send_login(bot: Bot, ev: Event, url):
    at_sender = True if ev.group_id else False

    if WutheringWavesConfig.get_config("WavesQRLogin").data:
        path = Path(__file__).parent / f"{ev.user_id}.gif"

        im = [
            f"{game_title} 您的id为【{ev.user_id}】\n",
            "请扫描下方二维码获取登录地址，并复制地址到浏览器打开\n",
            MessageSegment.image(await get_qrcode_base64(url, path, ev.bot_id)),
        ]

        if WutheringWavesConfig.get_config("WavesLoginForward").data:
            if not ev.group_id and ev.bot_id == "onebot":
                # 私聊+onebot 不转发
                await bot.send(im)
            else:
                await bot.send(MessageSegment.node(im))
        else:
            await bot.send(im, at_sender=at_sender)

        if path.exists():
            path.unlink()
    else:
        if WutheringWavesConfig.get_config("WavesTencentWord").data:
            url = f"https://docs.qq.com/scenario/link.html?url={url}"
        im = [
            f"{game_title} 您的id为【{ev.user_id}】",
            "请复制地址到浏览器打开",
            f" {url}",
            "登录地址10分钟内有效",
        ]

        if WutheringWavesConfig.get_config("WavesLoginForward").data:
            if not ev.group_id and ev.bot_id == "onebot":
                # 私聊+onebot 不转发
                await bot.send("\n".join(im))
            else:
                await bot.send(MessageSegment.node(im))
        else:
            await bot.send("\n".join(im), at_sender=at_sender)


async def page_login_local(bot: Bot, ev: Event, url):
    at_sender = True if ev.group_id else False
    user_token = get_token(ev.user_id)
    await send_login(bot, ev, f"{url}/waves/i/{user_token}")
    result = cache.get(user_token)
    if isinstance(result, dict):
        return

    # 登录 - 并行国服登入缓存，增加国际服登入支持
    data = {
        "mobile": -1,
        "code": -1,
        "user_id": ev.user_id,
        "bot_id": ev.bot_id,
        "group_id": ev.group_id,
        "email": -1,
        "password": -1,
        "login_type": None,
        "msg": None,
    }
    cache.set(user_token, data)
    try:
        async with timeout(600):
            while True:
                result = cache.get(user_token)
                if result is None:
                    return await bot.send("登录超时!\n", at_sender=at_sender)

                # 檢查是否為國際服登入
                if result.get("login_type") == "international":
                    if result.get("email") != -1 and result.get("password") != -1:
                        await bot.send(result["msg"], at_sender=at_sender)
                        cache.delete(user_token)
                        return 

                elif result.get("mobile") != -1 and result.get("code") != -1:
                    text = f"{result['mobile']},{result['code']}"
                    cache.delete(user_token)
                    return await code_login(bot, ev, text, True)

                await asyncio.sleep(1)
    except asyncio.TimeoutError:
        return await bot.send("登录超时!\n", at_sender=at_sender)
    except Exception as e:
        logger.error(e)


async def page_login_other(bot: Bot, ev: Event, url):
    at_sender = True if ev.group_id else False
    user_token = get_token(ev.user_id)

    auth = {"bot_id": ev.bot_id, "user_id": ev.user_id}

    token = cache.get(user_token)
    if isinstance(token, str):
        await send_login(bot, ev, f"{url}/waves/i/{token}")
        return

    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                url + "/waves/token",
                json=auth,
                headers={"Content-Type": "application/json"},
            )
            token = r.json().get("token", "")
        except Exception as e:
            token = ""
            logger.error(e)
        if not token:
            return await bot.send("登录服务请求失败! 请稍后再试\n", at_sender=at_sender)

        await send_login(bot, ev, f"{url}/waves/i/{token}")

        cache.set(user_token, token)
        times = 3
        async with timeout(600):
            while True:
                if times <= 0:
                    return await bot.send(
                        "登录服务请求失败! 请稍后再试\n", at_sender=at_sender
                    )

                result = await client.post(url + "/waves/get", json={"token": token})
                if result.status_code != 200:
                    times -= 1
                    await asyncio.sleep(5)
                    continue
                data = result.json()
                if not data.get("ck"):
                    await asyncio.sleep(1)
                    continue

                waves_user = await add_cookie(ev, data["ck"], data["did"])
                cache.delete(user_token)
                if waves_user and isinstance(waves_user, WavesUser):
                    return await login_success_msg(bot, ev, waves_user)
                else:
                    if isinstance(waves_user, str):
                        return await bot.send(waves_user, at_sender=at_sender)
                    else:
                        return await bot.send(msg_error, at_sender=at_sender)


async def page_login(bot: Bot, ev: Event):
    url, is_local = await get_url()
    is_local = True  # 強制本地, page_login_other不好改国际服登录

    if is_local:
        return await page_login_local(bot, ev, url)
    else:
        return await page_login_other(bot, ev, url)


async def code_login(bot: Bot, ev: Event, text: str, isPage=False):
    at_sender = True if ev.group_id else False
    game_title = "[鸣潮]"
    # 手机+验证码
    try:
        phone_number, code = text.split(",")
        if not is_valid_chinese_phone_number(phone_number):
            raise ValueError("Invalid phone number")
    except ValueError as _:
        return await bot.send(
            f"{game_title} 手机号+验证码登录失败\n\n请参照以下格式:\n{PREFIX}登录 手机号,验证码\n",
            at_sender=at_sender,
        )

    did = str(uuid.uuid4()).upper()
    result = await waves_api.login(phone_number, code, did)
    if not result.success:
        return await bot.send(result.throw_msg(), at_sender=at_sender)

    if result.msg == "系统繁忙，请稍后再试":
        # 可能是没注册库街区。 -_-||
        return await bot.send(msg_error, at_sender=at_sender)

    if not result.data or not isinstance(result.data, dict):
        return await bot.send(message=result.throw_msg(), at_sender=at_sender)

    token = result.data.get("token", "")
    waves_user = await add_cookie(ev, token, did)
    if waves_user and isinstance(waves_user, WavesUser):
        return await login_success_msg(bot, ev, waves_user)
    else:
        if isinstance(waves_user, str):
            return await bot.send(waves_user, at_sender=at_sender)
        else:
            return await bot.send(msg_error, at_sender=at_sender)


async def add_cookie(ev, token, did) -> Union[WavesUser, str, None]:
    ck_res = await deal.add_cookie(ev, token, did)
    if "成功" in ck_res:
        user = await WavesUser.get_user_by_attr(ev.user_id, ev.bot_id, "cookie", token)
        if user:
            data = await WavesBind.insert_waves_uid(
                ev.user_id, ev.bot_id, user.uid, ev.group_id, lenth_limit=9
            )
            if data == 0 or data == -2:
                await WavesBind.switch_uid_by_game(ev.user_id, ev.bot_id, user.uid)
        return user
    return ck_res


@app.get("/waves/i/{auth}")
async def waves_login_index(auth: str):
    temp = cache.get(auth)
    if temp is None:
        template = waves_templates.get_template("404.html")
        return HTMLResponse(template.render())
    else:
        from ..utils.api.api import MAIN_URL

        url, _ = await get_url()
        template = waves_templates.get_template("index.html")
        return HTMLResponse(
            template.render(
                server_url=url,
                auth=auth,
                userId=temp.get("user_id", ""),
                kuro_url=MAIN_URL,
            )
        )


@app.post("/waves/login")
async def waves_login(data: LoginModel):
    temp = cache.get(data.auth)
    if temp is None:
        return {"success": False, "msg": "登录超时"}

    temp.update(data.model_dump())
    cache.set(data.auth, temp)
    return {"success": True}


@app.post("/waves/international/login")
async def waves_international_login(data: InternationalLoginModel):
    exist = cache.get(data.auth)
    if exist is None:
        return {"success": False, "msg": "登录超时"}

    from ..utils.api.kuro_py_api import login_overseas
    login_signal = await login_overseas(
        exist["user_id"], 
        exist["bot_id"], 
        exist["group_id"], 
        data.email, 
        data.password,
        data.geetest_data,
    )

    if login_signal.get("success", False): # 登录成功，更新缓存状态
        exist.update({
            "email": 1,
            "password": 1,
            "login_type": "international",
            "msg": login_signal.get("msg", "登录成功\n")
        })
        cache.set(data.auth, exist) # 更新缓存,准备结束

    return login_signal
