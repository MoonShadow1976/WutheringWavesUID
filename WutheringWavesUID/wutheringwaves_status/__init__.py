from gsuid_core.status.plugin_status import register_status

from ..utils.database.models import WavesBind, WavesUser
from ..utils.image import get_ICON


async def get_user_num():
    datas = await WavesUser.get_waves_all_user()
    return len(datas)


async def get_add_num():
    datas = await WavesBind.get_all_data()
    return len(datas)


async def get_sign_num():
    datas = await WavesUser.get_waves_all_user()
    num = 0
    for data in datas:
        if data.sign_switch != "off":
            num += 1
    return num


register_status(
    get_ICON(),
    "WutheringWavesUID",
    {
        "绑定UID": get_add_num,
        "登录账户": get_user_num,
        "开启签到": get_sign_num,
    },
)
