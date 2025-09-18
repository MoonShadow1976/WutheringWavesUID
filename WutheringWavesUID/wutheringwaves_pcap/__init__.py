import json
import tempfile
import time
import atexit
from pathlib import Path
from typing import Optional

import aiohttp
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from .pcap_api import pcap_api
from .pcap_parser import PcapDataParser
from .optimized_pcap_handler import optimized_handler
from ..utils.at_help import ruser_id
from ..utils.database.models import WavesBind
from ..utils.error_reply import WAVES_CODE_103
from ..utils.hint import error_reply

# 使用簡單的 SV 實例，參考現有指令
sv_pcap_parse = SV("pcap解析", priority=5)
sv_pcap_status = SV("pcap状态", priority=5)
sv_pcap_file = SV("pcap文件处理", priority=5, area="DIRECT")
sv_pcap_data = SV("pcap数据", priority=5)
sv_pcap_analysis = SV("pcap分析", priority=5)


# 臨時文件清理函數
def safe_unlink(file_path: Path, max_retries: int = 3):
    """安全地刪除文件，處理 Windows 權限問題"""
    for attempt in range(max_retries):
        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  # 遞增等待時間
            else:
                logger.warning(f"無法刪除臨時文件: {file_path}")
                return False
        except Exception as e:
            logger.warning(f"刪除臨時文件時發生錯誤: {e}")
            return False
    return False


# 文件處理指令 - qq 用户使用（官方bot暂不支持）
@sv_pcap_file.on_file(("pcap"))
async def pcap_file_handler(bot: Bot, ev: Event):
    """pcap 文件處理指令 - 使用優化處理器"""
    user_id = ruser_id(ev)
    logger.info(f"[鳴潮pcap] 用戶 {user_id} 上傳了 pcap 文件")

    if not ev.file:
        return await bot.send("文件上傳失敗，請重新上傳")

    # 使用優化的處理器
    success = await optimized_handler.handle_pcap_file(bot, ev, ev.file)

    if not success:
        await bot.send("文件處理失敗，請檢查文件格式或重試")


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
    user_id = ruser_id(ev)
    logger.info(f"[鳴潮pcap] 用戶 {user_id} 觸發了解析指令")

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
            return await bot.send("請上傳 .pcap 或 .pcapng 格式的文件")

        # 檢查文件大小
        if file_size > 50 * 1024 * 1024:  # 50MB
            return await bot.send("文件過大，請上傳小於 50MB 的文件")

        await bot.send("正在解析 pcap 文件，請稍候...")

        try:
            # 創建臨時文件
            with tempfile.NamedTemporaryFile(
                suffix=Path(file_name).suffix, delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)

            # 下載文件
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    file_content = await response.read()
                    temp_path.write_bytes(file_content)

            # 調用 pcap API 解析
            result = await pcap_api.parse_pcap_file(str(temp_path))

            # 清理臨時文件
            safe_unlink(temp_path)

            if not result:
                return await bot.send("解析失敗：API 返回空結果")

            # 檢查結果是否包含錯誤信息
            if isinstance(result, dict) and result.get("error"):
                return await bot.send(f"解析失敗：{result.get('error', '未知錯誤')}")

            # 解析數據
            # 檢查結果是否包含數據
            if not isinstance(result, dict) or "data" not in result:
                return await bot.send("解析失敗：沒有返回數據")

            if result.get("data") is None:
                return await bot.send("解析失敗：數據為空")

            parser = PcapDataParser()
            waves_data = await parser.parse_pcap_data(result["data"])

            if not waves_data:
                return await bot.send(
                    "數據解析失敗，請檢查 pcap 文件是否包含有效的鳴潮數據"
                )


            # 發送成功消息
            # 從解析器中獲取統計信息
            total_roles = len(waves_data)
            total_weapons = len(parser.weapon_data)
            total_phantoms = len(parser.phantom_data)

            success_msg = f"""✅ pcap 數據解析成功！

                📊 解析結果：
                • 角色數量：{total_roles}
                • 武器數量：{total_weapons}  
                • 聲骸數量：{total_phantoms}

                🎯 現在可以使用「刷新面板」查看詳細數據了！"""

            await bot.send(success_msg)

        except Exception as e:
            logger.exception(f"pcap 解析失敗: {e}")
            await bot.send(f"解析過程中發生錯誤：{str(e)}")
    else:
        # 沒有附件，檢查是否有已解析的數據
        pcap_data = await load_pcap_data(user_id)

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
                    total_phantoms += len(phantom_data.get("equipPhantomList", []))

            status_msg = f"""✅ 已找到 pcap 數據

                📊 數據統計：
                • 角色數量：{total_roles}
                • 武器數量：{total_weapons}
                • 聲骸數量：{total_phantoms}

                💡 現在可以使用「刷新面板」查看詳細數據"""

            await bot.send(status_msg)
        else:
            await bot.send("❌ 未找到 pcap 數據，請先上傳 pcap 文件")


# 狀態指令 - 使用 on_fullmatch，參考 "刷新面板" 指令
@sv_pcap_status.on_fullmatch(
    (
        "pcap状态",
        "pcap检查",
    ),
    block=True,
)
async def pcap_status(bot: Bot, ev: Event):
    """pcap 狀態指令"""
    user_id = ruser_id(ev)
    logger.info(f"[鳴潮pcap] 用戶 {user_id} 檢查 pcap 狀態")

    # 檢查是否有 pcap 數據
    pcap_data = await load_pcap_data(user_id)

    if pcap_data:
        total_roles = pcap_data.get("total_roles", 0)
        total_weapons = pcap_data.get("total_weapons", 0)
        total_phantoms = pcap_data.get("total_phantoms", 0)

        status_msg = f"""✅ pcap 數據已加載

            📊 數據統計：
            • 角色數量：{total_roles}
            • 武器數量：{total_weapons}
            • 聲骸數量：{total_phantoms}

            💡 現在可以使用「刷新面板」查看詳細數據"""

        await bot.send(status_msg)
    else:
        await bot.send("❌ 未找到 pcap 數據，請先上傳並解析 pcap 文件")



async def load_pcap_data(uid: str) -> Optional[dict]:
    """加載 pcap 數據"""
    try:
        data_file = Path("data/pcap_data") / uid / "latest_data.json"

        if not data_file.exists():
            return None

        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"加載 pcap 數據失敗: {e}")
        return None
