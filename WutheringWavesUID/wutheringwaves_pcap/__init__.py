import json
from pathlib import Path
import tempfile

import aiohttp
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..utils.database.models import WavesBind
from ..utils.error_reply import WAVES_CODE_097, WAVES_CODE_103
from ..utils.hint import error_reply
from ..wutheringwaves_config import PREFIX, WutheringWavesConfig
from .pcap_api import pcap_api
from .pcap_file_handler import PcapFileHandler
from .pcap_parser import PcapDataParser
from .upload import page_upload

sv_pcap_upload = SV("pcap上传")
sv_pcap_parse = SV("pcap解析")
sv_pcap_file = SV("pcap文件处理")
sv_pcap_help = SV("pcap帮助")


@sv_pcap_upload.on_fullmatch(("上传pcap", "pcap上传", "upload pcap"), block=True)
async def pcap_upload(bot: Bot, ev: Event):
    """pcap 上传"""
    return await page_upload(bot, ev)


# 文件處理指令 - qq 用户使用（官方bot暂不支持）
@sv_pcap_file.on_file("pcap")
async def pcap_file_handler(bot: Bot, ev: Event):
    """pcap 文件處理指令 - 使用優化處理器"""
    at_sender = True if ev.group_id else False

    pcap_handler = PcapFileHandler()
    msg = await pcap_handler.handle_pcap_file(bot, ev, ev.file)

    await bot.send(msg, at_sender)


# 解析指令 - discord 用户使用
@sv_pcap_parse.on_fullmatch(
    (
        "解析pcap",
        "pcap解析",
    ),
    block=True,
)
async def pcap_parse(bot: Bot, ev: Event):
    """pcap 解析指令"""
    at_sender = True if ev.group_id else False
    uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)

    # 檢查是否有附件文件
    attachment_file = None
    for msg in ev.content:
        if msg.type == "attachment":
            attachment_file = msg.data
            break

    if attachment_file:
        # 如果有附件，處理文件
        file_name = attachment_file.get("filename", "")
        file_url = attachment_file.get("url", "")
        file_size = attachment_file.get("size", 0)

        # 檢查文件格式
        if not file_name.lower().endswith((".pcap", ".pcapng")):
            return await bot.send("文件格式错误，请上传 .pcap 或 .pcapng 文件\n", at_sender)

        # 檢查文件大小
        if file_size > 50 * 1024 * 1024:  # 50MB
            return await bot.send("文件过大，请上传小于 50MB 的文件\n", at_sender)

        try:
            # 創建臨時文件
            with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            # 下載文件
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    file_content = await response.read()
                    temp_path.write_bytes(file_content)

            # 調用 pcap API 解析
            result = await pcap_api.parse_pcap_file(temp_path)

            # 清理臨時文件
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception as e:
                logger.warning(f"清理临时文件 {temp_path} 时发生异常: {e}")
                pass

            if not result:
                return await bot.send("解析失败：API 返回空结果\n", at_sender)

            # 檢查結果是否包含錯誤信息
            if isinstance(result, dict) and result.get("error"):
                return await bot.send(f"解析失败：{result.get('error', '未知错误')}\n", at_sender)

            # 解析數據
            # 檢查結果是否包含數據
            if not isinstance(result, dict) or "data" not in result:
                return await bot.send("解析失败：API 没有返回数据\n", at_sender)

            if result.get("data") is None:
                return await bot.send("解析失败：返回数据为空\n", at_sender)

            parser = PcapDataParser()
            waves_data = await parser.parse_pcap_data(result["data"])

            if not waves_data:
                return await bot.send("数据解析失败，请确保 pcap 文件包含有效的鸣潮数据\n", at_sender)

            # 發送成功消息
            # 從解析器中獲取統計信息
            total_roles = len(waves_data)
            total_weapons = len(parser.weapon_data)
            total_phantoms = len(parser.phantom_data)

            msg = [
                "✅ pcap 数据解析成功！",
                f"📊 解析結果(uid:{parser.account_info.id})：",
                f"• 角色数量：{total_roles}",
                f"• 武器数量：{total_weapons}",
                f"• 声骸套数：{total_phantoms}",
                "",
                f"🎯 现在可以使用「{PREFIX}刷新面板」更新到您的数据里了！",
                "",
            ]

            await bot.send("\n".join(msg), at_sender)

        except Exception as e:
            logger.exception(f"pcap 解析失敗: {e}")
            await bot.send(f"解析过程中发生错误：{str(e)}\n", at_sender)
    else:
        if not uid:
            return await bot.send(error_reply(WAVES_CODE_103), at_sender)

        # 沒有附件，檢查是否有已解析的數據
        pcap_data = await load_pcap_data(uid)

        if pcap_data:
            # 從角色詳細數據中獲取統計信息
            role_detail_list = pcap_data.get("role_detail_list", [])
            total_roles = len(role_detail_list)

            # 統計武器和聲骸
            total_weapons = 0
            total_phantoms = 0

            for role_detail in role_detail_list:
                # 檢查武器
                weapon_data = role_detail.get("weaponData", {})
                if weapon_data and weapon_data.get("weapon", {}).get("weaponId", 0) > 0:
                    total_weapons += 1

                # 檢查聲骸
                phantom_data = role_detail.get("phantomData", {})
                if phantom_data and phantom_data.get("equipPhantomList"):
                    total_phantoms += 1

            msg = [
                "❌ 未上传 pcap 文件！",
                "📊 已有解析結果：",
                f"• 角色数量：{total_roles}",
                f"• 武器数量：{total_weapons}",
                f"• 声骸套数：{total_phantoms}",
                "",
            ]

            await bot.send("\n".join(msg), at_sender)
        else:
            await bot.send(error_reply(WAVES_CODE_097), at_sender)


@sv_pcap_help.on_fullmatch(
    (
        "pcap帮助",
        "pcap help",
    ),
    block=True,
)
async def pcap_help(bot: Bot, ev: Event):
    """Wuthery pcap 数据导入帮助"""
    url = "https://wuthery.COM/guides"
    if WutheringWavesConfig.get_config("WavesTencentWord").data:
        url = f"https://docs.qq.COM/scenario/link.html?url={url}"

    warn = "\n".join(
        [
            "导入前请注意：",
            "1. 此方法通过抓取游戏网络数据包实现，可直接导入所有角色面板数据",
            # "3. 用户账号系统（云端保存与同步）即将上线",
            "2. 加速器等网络工具可能导致抓包失败",
            "3. 请关闭其他可能产生大量网络数据包的软件，确保pcap文件体积不超过4MB（文件过大可能导致解析失败）",
            "4. 请勿上传含有隐私信息的 .pcap 文件",
            f"5. 具体教程请前往[ {url} ]查看, 内有视频教程，可参考操作",
            "\n",
        ]
    )
    method = "\n".join(
        [
            "【PC端方法】使用 Wireshark:",
            "1. 安装 Wireshark 并打开",
            "2. 启动鸣潮游戏，进入登录界面（男女主角界面）",
            "3. 在Wireshark中选择您连接互联网的网络接口",
            "4. 切换回游戏并登录进入游戏世界（进度条开始加载时即可停止抓包）",
            "5. 返回Wireshark停止抓包，并保存为 .pcap 文件",
            "6. 前往导入页面，上传刚才保存的 .pcap 文件",
            "注意：也可以使用其他能导出 .pcap 文件的抓包工具",
            "\n",
            "【安卓端方法】使用 PCAPdroid:",
            "1. 安装 PCAPdroid，在 Traffic dump 选 .pcap 文件",
            "2. Target apps 中选择 Wuthering Waves",
            "3. 点击“Ready”，然后启动并进入游戏",
            "4. 返回 PCAPdroid 停止抓包，生成文件并上传",
            "\n",
        ]
    )
    upload_note = "\n".join(
        [
            "【上传方法】:",
            f"使用命令[{PREFIX}上传pcap]访问网页上传 .pcap 文件  --推荐",
            "• qq用户请直接发送 .pcap 文件到本群或私聊机器人(qq官方bot暂不支持)",
            f"• discord用户请使用命令[{PREFIX}解析pcap]并上传 .pcap 文件为附件",
            "• 其他平台暂未测试",
            "\n",
        ]
    )
    msg = [warn, method, upload_note]

    await bot.send(msg)


async def load_pcap_data(uid: str) -> dict | None:
    """加載 pcap 數據"""
    try:
        data_file = Path("data/pcap_data") / uid / "latest_data.json"

        if not data_file.exists():
            return None

        with open(data_file, encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"加載 pcap 數據失敗: {e}")
        return None


async def exist_pcap_data(uid: str) -> bool:
    """判断 pcap 數據是否存在"""
    try:
        data_file = Path("data/pcap_data") / uid / "latest_data.json"

        if not data_file.exists():
            return False

        return True
    except Exception as e:
        logger.error(f"判断 pcap 數據是否存在失敗: {e}")
        return False
