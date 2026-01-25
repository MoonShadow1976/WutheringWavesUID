import asyncio
import hashlib
from pathlib import Path
import tempfile

from async_timeout import timeout
from fastapi import File, UploadFile
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from gsuid_core.utils.cookie_manager.qrlogin import get_qrcode_base64
from gsuid_core.web_app import app
from pydantic import BaseModel
from starlette.responses import HTMLResponse

from ..utils.bot_url import get_url
from ..utils.cache import TimedCache
from ..utils.resource.RESOURCE_PATH import waves_templates
from ..wutheringwaves_config import PREFIX, WutheringWavesConfig
from .pcap_api import pcap_api
from .pcap_parser import PcapDataParser

# 文件上传缓存，10分钟过期
upload_cache = TimedCache(timeout=600, maxsize=10)
parser = PcapDataParser()


def get_token(userId: str):
    """生成用户token"""
    return hashlib.sha256(userId.encode()).hexdigest()[:8]


async def send_url(bot: Bot, ev: Event, url):
    at_sender = True if ev.group_id else False

    if WutheringWavesConfig.get_config("WavesQRLogin").data:
        path = Path(__file__).parent / f"{ev.user_id}.gif"

        im = [
            f"[鸣潮][文件上传] 您的id为【{ev.user_id}】\n",
            "请扫描下方二维码获取上传地址，并复制地址到浏览器打开\n",
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
            url = f"https://docs.qq.COM/scenario/link.html?url={url}"
        im = [
            f"[鸣潮][文件上传] 您的id为【{ev.user_id}】",
            "请复制地址到浏览器打开",
            f" {url}",
            "链接10分钟内有效",
        ]

        if WutheringWavesConfig.get_config("WavesLoginForward").data:
            if not ev.group_id and ev.bot_id == "onebot":
                # 私聊+onebot 不转发
                await bot.send("\n".join(im))
            else:
                await bot.send(MessageSegment.node(im))
        else:
            await bot.send("\n".join(im), at_sender=at_sender)


async def send_upload_link(bot: Bot, ev: Event, url: str):
    """发送文件上传链接"""
    at_sender = True if ev.group_id else False
    user_token = get_token(ev.user_id)
    await send_url(bot, ev, f"{url}/waves/upload/{user_token}")

    result = upload_cache.get(user_token)
    if isinstance(result, dict):
        return

    # 初始化上传缓存
    data = {
        "msg": "",
        "upload_complete": False,
    }
    upload_cache.set(user_token, data)

    try:
        async with timeout(600):
            while True:
                result = upload_cache.get(user_token)
                if result is None:
                    return await bot.send("上传超时!\n", at_sender=at_sender)

                if result.get("upload_complete"):
                    msg = result.get("msg", "")
                    upload_cache.delete(user_token)
                    return await bot.send(msg, at_sender=at_sender)

                await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"等待上传异常: {e}")


async def page_upload(bot: Bot, ev: Event):
    url, is_local = await get_url()
    is_local = True

    if is_local:
        return await send_upload_link(bot, ev, url)
    else:
        pass


# 定义上传数据模型
class UploadModel(BaseModel):
    auth: str


class ResultModel(BaseModel):
    success: bool
    msg: str
    error_code: str = ""


async def handle_file_list(files: list[UploadFile]) -> ResultModel:
    """处理上传的文件列表"""
    success_num = 0
    fail_num = 0
    success_msg = []
    fail_msg = []

    success_msg.append(f"✅ pcap 数据解析成功！\n🎯 现在可以使用「{PREFIX}刷新面板」更新到您的数据里了！\n")

    for file in files:
        # 检查文件大小（最大5MB）
        max_size = 5 * 1024 * 1024

        # 读取文件内容
        content = await file.read()
        file_size = len(content)

        if file_size > max_size:
            fail_num += 1
            fail_msg.append("❌ 文件过大，请上传小于 5MB 的文件！")
            continue

        # 检查文件扩展名
        if not file.filename or not file.filename.lower().endswith(".pcap"):
            fail_num += 1
            fail_msg.append("❌ 文件格式错误，请上传 .pcap 文件！")
            continue

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".pcap", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)

        try:
            # 调用pcap API解析
            result = await pcap_api.parse_pcap_file(temp_path)
            if not isinstance(result, dict) or result.get("data") is None:
                fail_num += 1
                fail_msg.append(f"❌ {file.filename} 文件解析失败，返回数据为空")
                continue
            if isinstance(result, dict) and result.get("error"):
                fail_num += 1
                fail_msg.append(f"❌ {file.filename} 文件解析失败，{result.get('error', '未知错误')}")
                continue

            # 解析数据
            waves_data = await parser.parse_pcap_data(result["data"])

            # 删除临时文件
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception as e:
                logger.warning(f"清理临时文件 {temp_path} 时发生异常: {e}")
                pass

            if not waves_data:
                fail_num += 1
                fail_msg.append(f"❌ {file.filename} 文件数据解析失败，请确保包含有效的鸣潮数据")
                continue

            # 从解析器中获取统计信息
            msg = [
                f"📊 解析結果(uid:{parser.account_info.id})：",
                f"• 角色数量：{len(waves_data)}",
                f"• 武器数量：{len(parser.weapon_data)}",
                f"• 声骸套数：{len(parser.phantom_data)}",
            ]
            success_num += 1
            success_msg.append("\n".join(msg))

        except Exception as e:
            logger.error(f"处理文件 {file.filename} 异常: {e}")
            fail_num += 1
            fail_msg.append(f"❌ {file.filename} 文件解析异常: {e}")
            # 清理临时文件
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                logger.warning(f"清理临时文件 {temp_path} 时发生异常: {e}")
                pass
            continue

    fail_msg.append(f"\n或请使用「{PREFIX}pcap帮助」获取具体使用方法！")

    if success_num > 0:
        return ResultModel(
            success=True,
            msg=f"成功：{success_num}个文件，失败：{fail_num}个文件\n" + "\n".join(success_msg),
            error_code="",
        )
    else:
        return ResultModel(
            success=False,
            msg=f"全部文件解析失败，个数：{fail_num}\n" + "\n".join(fail_msg),
            error_code="ALL_FAILED",
        )


@app.get("/waves/upload/{auth}")
async def waves_upload_index(auth: str):
    """文件上传页面"""
    temp = upload_cache.get(auth)
    if temp is None:
        template = waves_templates.get_template("404.html")
        return HTMLResponse(template.render())
    else:
        url, _ = await get_url()
        template = waves_templates.get_template("upload.html")
        return HTMLResponse(
            template.render(
                server_url=url,
                auth=auth,
                userId=temp.get("user_id", ""),
            )
        )


@app.post("/waves/upload_files/{auth}")
async def waves_upload_files(auth: str, files: list[UploadFile] = File(...)):
    """处理文件上传"""
    temp = upload_cache.get(auth)
    if temp is None:
        return {"success": False, "msg": "上传链接已过期", "error_code": "EXPIRED"}

    upload_signal = await handle_file_list(files)
    if upload_signal.success:
        temp.update({"upload_complete": True, "msg": upload_signal.msg})
        upload_cache.set(auth, temp)

    return {"success": upload_signal.success, "msg": upload_signal.msg, "error_code": upload_signal.error_code}
