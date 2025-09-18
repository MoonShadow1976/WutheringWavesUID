#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
優化的 PCAP 處理器
整合增強版解析器，提供更好的數據整理和展示
"""

import tempfile
import time
from pathlib import Path
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from .pcap_parser import PcapDataParser
from ..utils.at_help import ruser_id
from .pcap_api import pcap_api


class OptimizedPcapHandler:
    """優化的 PCAP 處理器"""

    def __init__(self, data_dir: str = "zh-Hant"):
        self.parser = PcapDataParser()

    async def handle_pcap_file(self, bot: Bot, ev: Event, file) -> bool:
        """處理 PCAP 文件上傳"""
        user_id = ruser_id(ev)
        logger.info(f"[鳴潮pcap] 用戶 {user_id} 上傳了 pcap 文件")

        if not file:
            await bot.send("文件上傳失敗，請重新上傳")
            return False

        file_name = ev.file_name

        # 檢查文件格式
        if not file_name or not file_name.lower().endswith(('.pcap')):
            await bot.send("請上傳 .pcap 格式的文件")
            return False

         # 檢查文件大小 (通过 Base64 字符串长度估算)
        base64_data = file
        estimated_size = (len(base64_data) * 3) / 4 - base64_data.count('=', -2)  # 估算实际文件大小
        
        if estimated_size > 50 * 1024 * 1024:  # 50MB
            await bot.send("文件過大，請上傳小於 50MB 的文件")
            return False

        await bot.send("正在解析 pcap 文件，請稍候...")

        try:
            # 創建臨時文件
            with tempfile.NamedTemporaryFile(
                suffix=Path(file_name).suffix, delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)

            # 下載文件
            try:
                import base64
                # 移除可能的数据URI前缀（如果有的话）
                if ',' in base64_data:
                    base64_data = base64_data.split(',', 1)[1]
                    
                file_content = base64.b64decode(base64_data)
                temp_path.write_bytes(file_content)
            except Exception as e:
                logger.error(f"Base64 解码失败: {e}")
                await bot.send("文件格式错误，请上传有效的 Base64 编码文件")
                return False

            # 調用 pcap API 解析
            result = await pcap_api.parse_pcap_file(str(temp_path))

            # 清理臨時文件
            self._safe_unlink(temp_path)

            if not result:
                await bot.send("解析失敗：API 返回空結果")
                return False

            # 檢查結果是否包含錯誤信息
            if isinstance(result, dict) and result.get('error'):
                await bot.send(f"解析失敗：{result.get('error', '未知錯誤')}")
                return False

            # 檢查結果是否包含數據
            if not isinstance(result, dict) or 'data' not in result:
                await bot.send("解析失敗：沒有返回數據")
                return False

            if result.get('data') is None:
                await bot.send("解析失敗：數據為空")
                return False

            # 解析數據
            waves_data = await self.parser.parse_pcap_data(result["data"])

            if not waves_data:
                await bot.send("數據解析失敗，請檢查 pcap 文件是否包含有效的鳴潮數據")
                return False

            # 發送成功消息
            # 從解析器中獲取統計信息
            total_roles = len(waves_data)
            total_weapons = len(self.parser.weapon_data)
            total_phantoms = len(self.parser.phantom_data)

            success_msg = f"""✅ pcap 數據解析成功！

                📊 解析結果：
                • 角色數量：{total_roles}
                • 武器數量：{total_weapons}  
                • 聲骸數量：{total_phantoms}

                🎯 現在可以使用「刷新面板」查看詳細數據了！"""

            await bot.send(success_msg)

            return True

        except Exception as e:
            logger.exception(f"pcap 解析失敗: {e}")
            await bot.send(f"解析過程中發生錯誤：{str(e)}")
            return False

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



# 創建全局實例
optimized_handler = OptimizedPcapHandler()
