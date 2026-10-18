from pathlib import Path
import tempfile
import time

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from ..wutheringwaves_config import PREFIX
from .pcap_api import pcap_api
from .pcap_parser import PcapDataParser


class PcapFileHandler:
    """PCAP 處理器"""

    def __init__(self):
        self.parser = PcapDataParser()

    async def handle_pcap_file(self, bot: Bot, ev: Event, file) -> str | list[str]:
        """處理 PCAP 文件上傳"""

        if not file:
            return "文件上传失败，请重新上传\n"

        file_name = ev.file_name

        # 檢查文件格式
        if not file_name or not file_name.lower().endswith(".pcap"):
            return "文件格式错误，请上传 .pcap 文件\n"

        # 檢查文件大小 (通过 Base64 字符串长度估算)
        base64_data = file
        estimated_size = (len(base64_data) * 3) / 4 - base64_data.count("=", -2)  # 估算实际文件大小

        if estimated_size > 50 * 1024 * 1024:  # 50MB
            return "文件过大，请上传小于 50MB 的文件\n"

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            # 下載文件
            try:
                import base64

                # 移除可能的数据URI前缀（如果有的话）
                if "," in base64_data:
                    base64_data = base64_data.split(",", 1)[1]

                file_content = base64.b64decode(base64_data)
                temp_path.write_bytes(file_content)
            except Exception as e:
                logger.error(f"Base64 解码失败: {e}")
                return "文件解析失败，请确保上传的是有效的 pcap 文件\n"

            # 調用 pcap API 解析
            result = await pcap_api.parse_pcap_file(temp_path)

            # 清理臨時文件
            self._safe_unlink(temp_path)

            if not result:
                return "解析失败：API 返回空结果\n"

            # 檢查結果是否包含錯誤信息
            if isinstance(result, dict) and result.get("error"):
                return f"解析失败：{result.get('error', '未知错误')}\n"

            # 檢查結果是否包含數據
            if not isinstance(result, dict) or "data" not in result:
                return "解析失败：API 没有返回数据\n"

            if result.get("data") is None:
                return "解析失败：返回数据为空\n"

            # 解析數據
            waves_data = await self.parser.parse_pcap_data(result["data"])

            if not waves_data:
                return "数据解析失败，请确保 pcap 文件包含有效的鸣潮数据\n"

            # 發送成功消息
            # 從解析器中獲取統計信息
            msg = [
                "✅ pcap 数据解析成功！",
                f"📊 解析結果(uid:{self.parser.account_info.id})：",
                f"• 成就数量：{self.parser.account_info.achievementCount}",
                f"• 成就星数：{self.parser.account_info.achievementStar}",
                f"• 角色数量：{len(waves_data)}",
                f"• 武器数量：{len(self.parser.weapon_data)}",
                f"• 声骸套数：{len(self.parser.phantom_data)}",
                "",
                f"🎯 现在可以使用「{PREFIX}刷新面板」更新到您的数据里了！",
                "",
            ]

            return "\n".join(msg)

        except Exception as e:
            logger.exception(f"pcap 解析失敗: {e}")
            return f"解析过程中发生错误：{str(e)}\n"

    def _safe_unlink(self, file_path: Path, max_retries: int = 3):
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
