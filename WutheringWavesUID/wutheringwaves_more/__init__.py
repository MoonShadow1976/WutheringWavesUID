from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..utils.at_help import ruser_id
from ..utils.hint import error_reply
from .draw_poker import draw_poker_img
from ..utils.waves_api import waves_api
from ..utils.database.models import WavesBind
from ..utils.error_reply import WAVES_CODE_103, WAVES_CODE_098

sv_waves_poker = SV("waves查询牌局")


@sv_waves_poker.on_command(
    ("poker", "牌局", "扑克", "激斗", "打牌", "荣耀之丘"),
    block=True,
)
async def send_poker(bot: Bot, ev: Event):
    user_id = ruser_id(ev)
    uid = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    if not uid:
        return await bot.send(error_reply(WAVES_CODE_103))
    if waves_api.is_net(uid):
        return await bot.send(error_reply(WAVES_CODE_098))

    im = await draw_poker_img(ev, uid, user_id)
    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        return await bot.send(im, at_sender)
    elif isinstance(im, bytes):
        return await bot.send(im)
