# from .download_core import download_all_file
from .download_github import download_all_file

from .RESOURCE_PATH import (
    AVATAR_PATH,
    MATERIAL_PATH,
    PHANTOM_PATH,
    ROLE_DETAIL_PATH,
    ROLE_PILE_PATH,
    SHARE_BG_PATH,
    WEAPON_PATH,
    GUIDE_PATH,
)


async def download_all_resource():
    await download_all_file(
        "WutheringWavesUID",
        {
            "resource/waves_avatar": AVATAR_PATH,
            "resource/waves_weapon": WEAPON_PATH,
            "resource/role_pile": ROLE_PILE_PATH,
            "resource/role_detail": ROLE_DETAIL_PATH,
            #"resource/share": SHARE_BG_PATH,
            "resource/phantom": PHANTOM_PATH,
            "resource/material": MATERIAL_PATH,
            "resource/guide": GUIDE_PATH,
        },
    )
