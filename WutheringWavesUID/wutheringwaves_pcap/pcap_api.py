import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from gsuid_core.logger import logger


class PcapApi:
    """PCAP API 客戶端"""

    def __init__(self):
        self.base_url = "https://pcap.wuthery.com/v1"
        self.timeout = 30

    async def parse_pcap_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        上傳並解析 pcap 文件

        Args:
            file_path: pcap 文件路徑

        Returns:
            解析結果字典，如果失敗返回 None
        """
        try:
            file_path = Path(file_path)
            logger.debug(f"pcap path: {file_path}")
            if not file_path.exists():
                logger.error(f"PCAP 文件不存在: {file_path}")
                return None
            #  文件会冲突吗
            # 準備文件數據
            with open(file_path, "rb") as f:
                file_data = f.read()

            # 準備表單數據
            data = aiohttp.FormData()
            data.add_field(
                "file",
                file_data,
                filename=file_path.name,
                content_type="application/vnd.tcpdump.pcap",
            )

            # 發送請求
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.post(
                    f"{self.base_url}/parse", data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"PCAP 解析成功: {file_path.name}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"PCAP 解析失敗: {response.status} - {error_text}")
                        return None

        except asyncio.TimeoutError:
            logger.error(f"PCAP 解析超時: {file_path}")
            return None
        except Exception as e:
            logger.exception(f"PCAP 解析異常: {file_path}", e)
            return None


# 創建全局實例
pcap_api = PcapApi()
