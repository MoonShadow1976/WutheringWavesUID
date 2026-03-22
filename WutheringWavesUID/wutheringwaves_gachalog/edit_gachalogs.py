import asyncio
from datetime import datetime
import hashlib
import json
from pathlib import Path

from async_timeout import timeout
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from gsuid_core.utils.cookie_manager.qrlogin import get_qrcode_base64
from gsuid_core.web_app import app
from starlette.responses import HTMLResponse, JSONResponse

from ..utils.bot_url import get_url
from ..utils.cache import TimedCache
from ..utils.database.models import WavesBind
from ..utils.resource.RESOURCE_PATH import PLAYER_PATH, waves_templates
from ..wutheringwaves_config import WutheringWavesConfig

# 编辑缓存，有效期30分钟
TIMEOUT = 1800
edit_cache = TimedCache(timeout=TIMEOUT, maxsize=50)


def get_token(userId: str):
    """生成用户token"""
    return hashlib.sha256(userId.encode()).hexdigest()[:8]


async def send_edit_link(bot: Bot, ev: Event, url: str):
    """发送编辑链接并等待结果"""
    at_sender = True if ev.group_id else False
    user_token = get_token(ev.user_id)

    # 获取用户绑定的UID
    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
    if not uid:
        await bot.send("你还没有绑定鸣潮UID，请先使用`/鸣潮绑定UID`命令绑定。", at_sender=at_sender)
        return

    edit_url = f"{url}/waves/edit/{user_token}"
    await _send_url(bot, ev, edit_url)

    # 初始化缓存，存储用户ID、UID和权限等级
    data = {
        "user_id": ev.user_id,
        "uid": uid,
        "pm": ev.user_pm,  # 权限等级
        "complete": False,
        "msg": "",
        "create_time": datetime.now().timestamp(),
    }
    edit_cache.set(user_token, data)

    try:
        async with timeout(TIMEOUT):
            while True:
                result = edit_cache.get(user_token)
                if result is None:
                    return await bot.send("编辑链接已关闭！\n", at_sender=at_sender)
                if result.get("complete"):
                    msg = result.get("msg", "编辑完成！")
                    # edit_cache.delete(user_token)
                    await bot.send(msg, at_sender=at_sender)
                    result["complete"] = False  # 重置
                await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"等待编辑异常: {e}")


async def _send_url(bot: Bot, ev: Event, url: str):
    """发送URL给用户（支持二维码或文本）"""
    at_sender = True if ev.group_id else False
    if WutheringWavesConfig.get_config("WavesQRLogin").data:
        path = Path(__file__).parent / f"{ev.user_id}.gif"
        im = [
            f"[鸣潮][抽卡记录编辑] 您的id为【{ev.user_id}】\n",
            "请扫描下方二维码获取编辑地址，并复制地址到浏览器打开\n",
            MessageSegment.image(await get_qrcode_base64(url, path, ev.bot_id)),
        ]
        if WutheringWavesConfig.get_config("WavesLoginForward").data:
            if not ev.group_id and ev.bot_id == "onebot":
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
            f"[鸣潮][抽卡记录编辑] 您的id为【{ev.user_id}】",
            "请复制地址到浏览器打开",
            f" {url}",
            "链接10分钟内有效",
        ]
        if WutheringWavesConfig.get_config("WavesLoginForward").data:
            if not ev.group_id and ev.bot_id == "onebot":
                await bot.send("\n".join(im))
            else:
                await bot.send(MessageSegment.node(im))
        else:
            await bot.send("\n".join(im), at_sender=at_sender)


# ==================== 数据格式转换函数 ====================
def convert_storage_to_export(storage_data):
    """将存储格式（uid, data_time, data）转换为导出格式（info, list）"""
    export = {
        "info": {
            "uid": storage_data.get("uid", ""),
            "export_time": storage_data.get("data_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "export_app": "WutheringWavesUID",
            "export_app_version": "2.0.1",
            "export_timestamp": int(datetime.now().timestamp()),
            "version": "v2.0",
        },
        "list": [],
    }
    data = storage_data.get("data", {})
    for pool_type, records in data.items():
        for item in records:
            export["list"].append(
                {
                    "cardPoolType": pool_type,
                    "resourceId": item.get("resourceId"),
                    "qualityLevel": item.get("qualityLevel"),
                    "resourceType": item.get("resourceType"),
                    "name": item.get("name"),
                    "count": item.get("count", 1),
                    "time": item.get("time"),
                }
            )
    return export


def convert_export_to_storage(export_data, uid):
    """将导出格式转换为存储格式"""
    if export_data.get("info", {}).get("uid") != str(uid):
        raise ValueError("UID不匹配")
    storage = {"uid": str(uid), "data_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "data": {}}
    for item in export_data.get("list", []):
        pool_type = item.get("cardPoolType")
        if not pool_type:
            continue
        storage["data"].setdefault(pool_type, []).append(
            {
                "resourceId": item.get("resourceId"),
                "qualityLevel": item.get("qualityLevel"),
                "resourceType": item.get("resourceType"),
                "name": item.get("name"),
                "count": item.get("count", 1),
                "time": item.get("time"),
            }
        )
    return storage


# ==================== FastAPI 路由 ====================
@app.get("/waves/edit/{auth}")
async def waves_edit_index(auth: str):
    """返回编辑页面，传递权限等级"""
    temp = edit_cache.get(auth)
    if temp is None:
        template = waves_templates.get_template("404.html")
        return HTMLResponse(template.render())
    else:
        from .draw_gachalogs import gacha_type_meta_rename

        pool_types = list(gacha_type_meta_rename.keys())
        pool_types_json = json.dumps(pool_types)

        create_time = temp.get("create_time", datetime.now().timestamp())
        elapsed = datetime.now().timestamp() - create_time
        remaining = max(0, TIMEOUT - elapsed)

        url, _ = await get_url()
        template = waves_templates.get_template("gacha_editor.html")
        return HTMLResponse(
            template.render(
                server_url=url,
                auth=auth,
                userId=temp.get("user_id", ""),
                userPm=temp.get("pm", 6),  # 传递权限等级到前端
                poolTypes=pool_types_json,
                timeout=int(remaining),  # 传递剩余秒数
            )
        )


@app.get("/waves/edit_data/{auth}")
async def waves_edit_data_get(auth: str):
    """获取当前用户的抽卡记录数据"""
    temp = edit_cache.get(auth)
    if temp is None:
        return JSONResponse(status_code=404, content={"success": False, "msg": "链接已过期"})
    uid = temp.get("uid")
    if not uid:
        return JSONResponse(status_code=400, content={"success": False, "msg": "未找到UID"})

    gacha_log_path = PLAYER_PATH / str(uid) / "gacha_logs.json"
    if not gacha_log_path.exists():
        # 无记录，返回空数据
        export_data = {
            "info": {
                "uid": str(uid),
                "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "export_app": "WutheringWavesUID",
                "export_app_version": "2.0.1",
                "export_timestamp": int(datetime.now().timestamp()),
                "version": "v2.0",
            },
            "list": [],
        }
    else:
        try:
            with open(gacha_log_path, encoding="utf-8") as f:
                storage_data = json.load(f)
            export_data = convert_storage_to_export(storage_data)
        except Exception as e:
            logger.error(f"读取抽卡记录失败: {e}")
            return JSONResponse(status_code=500, content={"success": False, "msg": "读取数据失败"})

    return JSONResponse(content=export_data)


@app.post("/waves/edit_data/{auth}")
async def waves_edit_data_post(auth: str, data: dict):
    temp = edit_cache.get(auth)
    if temp is None:
        return JSONResponse(status_code=404, content={"success": False, "msg": "链接已过期"})

    pm = temp.get("pm", 6)

    # 确定目标UID
    if pm <= 1:  # 超级管理员：目标UID从前端数据获取
        target_uid = data.get("info", {}).get("uid")
        if not target_uid:
            return JSONResponse(status_code=400, content={"success": False, "msg": "目标UID未提供"})
        if not str(target_uid).isdigit() or len(str(target_uid)) != 9:
            return JSONResponse(status_code=400, content={"success": False, "msg": "UID格式错误"})
    else:  # 普通用户：只能保存自己的UID
        target_uid = temp.get("uid")
        if not target_uid:
            return JSONResponse(status_code=400, content={"success": False, "msg": "未找到UID"})

    try:
        if "list" not in data:
            return JSONResponse(status_code=400, content={"success": False, "msg": "数据格式错误"})

        storage_data = convert_export_to_storage(data, target_uid)  # 传入正确的目标UID
        gacha_log_path = PLAYER_PATH / str(target_uid) / "gacha_logs.json"
        gacha_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(gacha_log_path, "w", encoding="utf-8") as f:
            json.dump(storage_data, f, ensure_ascii=False, indent=4)

        temp["complete"] = True
        temp["msg"] = f"抽卡记录已更新，UID：{target_uid}"
        edit_cache.set(auth, temp)
        return JSONResponse(content={"success": True, "msg": "保存成功"})
    except Exception as e:
        logger.error(f"保存抽卡记录失败: {e}")
        return JSONResponse(status_code=500, content={"success": False, "msg": f"保存失败: {str(e)}"})


@app.post("/waves/fetch_gacha/{auth}")
async def waves_fetch_gacha(auth: str, data: dict):
    """根据UID获取抽卡记录，需要权限验证"""
    temp = edit_cache.get(auth)
    if temp is None:
        return JSONResponse(status_code=404, content={"success": False, "msg": "链接已过期"})

    pm = temp.get("pm", 6)
    uid_to_fetch = data.get("uid")
    if not uid_to_fetch:
        return JSONResponse(status_code=400, content={"success": False, "msg": "缺少UID"})

    # 权限验证：pm > 1 只能获取自己的UID；pm <= 1 可以获取任何UID
    if pm > 1 and str(uid_to_fetch) != str(temp.get("uid")):
        return JSONResponse(status_code=403, content={"success": False, "msg": "无权限获取其他用户数据"})

    gacha_log_path = PLAYER_PATH / str(uid_to_fetch) / "gacha_logs.json"
    if not gacha_log_path.exists():
        # 无记录，返回空数据
        export_data = {
            "info": {
                "uid": str(uid_to_fetch),
                "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "export_app": "WutheringWavesUID",
                "export_app_version": "2.0.1",
                "export_timestamp": int(datetime.now().timestamp()),
                "version": "v2.0",
            },
            "list": [],
        }
    else:
        try:
            with open(gacha_log_path, encoding="utf-8") as f:
                storage_data = json.load(f)
            export_data = convert_storage_to_export(storage_data)
        except Exception as e:
            logger.error(f"读取抽卡记录失败: {e}")
            return JSONResponse(status_code=500, content={"success": False, "msg": "读取数据失败"})

    return JSONResponse(content=export_data)


@app.delete("/waves/close/{auth}")
async def waves_close_edit(auth: str):
    """用户主动关闭页面时删除缓存"""
    temp = edit_cache.get(auth)
    if temp:
        edit_cache.delete(auth)
        return JSONResponse(content={"success": True, "msg": "已关闭"})
    else:
        return JSONResponse(status_code=404, content={"success": False, "msg": "链接已失效"})
