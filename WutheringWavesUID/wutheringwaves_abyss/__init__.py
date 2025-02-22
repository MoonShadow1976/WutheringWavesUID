from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV
from .draw_challenge_card import draw_challenge_img
from ..utils.database.models import WavesBind
from ..utils.error_reply import WAVES_CODE_103
from ..utils.hint import error_reply
from ..wutheringwaves_abyss.draw_abyss_card import draw_abyss_img

sv_waves_abyss = SV("waves查询深渊")
sv_waves_challenge = SV("waves查询全息")


@sv_waves_abyss.on_command(
    (
        f"查询深渊",
        f"sy",
        f"st",
        f"深渊",
        f"逆境深塔",
        f"深塔",
        f"超载",
        f"超载区",
        f"稳定",
        f"稳定区",
        f"实验",
        f"实验区",
    ),
    block=True,
)
async def send_waves_abyss_info(bot: Bot, ev: Event):
    await bot.logger.info("开始执行[鸣潮查询深渊信息]")

    user_id = ev.at if ev.at else ev.user_id
    uid = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    if not uid:
        return await bot.send(error_reply(WAVES_CODE_103))
    await bot.logger.info(f"[鸣潮查询深渊信息]user_id:{user_id} uid: {uid}")

    im = await draw_abyss_img(ev, uid, user_id)
    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        return await bot.send(im, at_sender)
    else:
        return await bot.send(im)


@sv_waves_challenge.on_command(
    (
        f"查询全息",
        f"查询全息战略",
        f"全息",
        f"全息战略",
    ),
    block=True,
)
async def send_waves_challenge_info(bot: Bot, ev: Event):
    await bot.logger.info("开始执行[鸣潮查询全息战略信息]")

    user_id = ev.at if ev.at else ev.user_id
    uid = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    if not uid:
        return await bot.send(error_reply(WAVES_CODE_103))
    await bot.logger.info(f"[鸣潮查询全息战略信息]user_id:{user_id} uid: {uid}")

    im = await draw_challenge_img(ev, uid, user_id)
    return await bot.send(im)
