# from .download_core import download_all_file
from gsuid_core.logger import logger

from .download_github import download_all_file
from .RESOURCE_PATH import (
    ALL_SKIN_PATH,
    AVATAR_PATH,
    GUIDE_PATH,
    MATERIAL_PATH,
    MONSTER_PATH,
    PHANTOM_PATH,
    ROLE_DETAIL_PATH,
    ROLE_PILE_PATH,
    SHARE_BG_PATH,
    WEAPON_PATH,
)


async def download_all_resource():
    """
    下载所有资源
    返回: 简化的下载结果字符串
    """
    result = await download_all_file(
        "WutheringWavesUID",
        {
            "resource/waves_avatar": AVATAR_PATH,
            "resource/waves_weapon": WEAPON_PATH,
            "resource/role_pile": ROLE_PILE_PATH,
            "resource/role_detail": ROLE_DETAIL_PATH,
            "resource/share": SHARE_BG_PATH,
            "resource/phantom": PHANTOM_PATH,
            "resource/monster": MONSTER_PATH,
            "resource/material": MATERIAL_PATH,
            "resource/guide": GUIDE_PATH,
            "resource/skin": ALL_SKIN_PATH,
        },
    )

    # 记录完整日志
    logger.info(f"📦 [资源下载完成] {result}")

    return result
