import re

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..wutheringwaves_config import WutheringWavesConfig
from .darw_rank_card import draw_rank_img
from .draw_all_rank_card import draw_all_rank_card
from .draw_bot_rank_card import draw_bot_rank_img
from .draw_gacha_server_rank import draw_gacha_server_rank_img
from .draw_local_total_rank_card import draw_local_total_rank
from .draw_total_rank_card import draw_total_rank
from .matrix_rank import draw_all_matrix_rank_card

sv_waves_rank_list = SV("ww角色排行")
sv_waves_rank_all_list = SV("ww角色总排行", priority=1)
sv_waves_rank_bot_list = SV("ww角色bot排行", priority=1)
sv_waves_rank_total_list = SV("ww练度总排行", priority=0)
sv_waves_gacha_server_rank = SV("ww抽卡全服排行", priority=0)
sv_waves_matrix_rank = SV("ww矩阵群排行", priority=-1)
sv_waves_matrix_rank_all = SV("ww矩阵总排行", priority=-1)


@sv_waves_rank_list.on_regex("^[\u4e00-\u9fa5]+(?:排行|排名)$", block=True)
async def send_rank_card(bot: Bot, ev: Event):
    # 正则表达式
    match = re.search(r"(?P<char>[\u4e00-\u9fa5]+)(?:排行|排名)", ev.raw_text)
    if not match:
        return
    ev.regex_dict = match.groupdict()
    char = match.group("char")

    if not ev.group_id:
        return await bot.send("请在群聊中使用")

    if not char:
        return

    rank_type = "伤害"
    if "评分" in char:
        rank_type = "评分"
    char = char.replace("伤害", "").replace("评分", "")

    if "练度" in char:
        im = await draw_local_total_rank(bot, ev)
    else:
        im = await draw_rank_img(bot, ev, char, rank_type)

    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        await bot.send(im, at_sender)
    if isinstance(im, bytes):
        await bot.send(im)


@sv_waves_rank_bot_list.on_regex("^[\u4e00-\u9fa5]+(?:bot排行|bot排名)$", block=True)
async def send_bot_rank_card(bot: Bot, ev: Event):
    botData = WutheringWavesConfig.get_config("botData").data
    if not botData:
        return await bot.send("[鸣潮] 未开启bot排行")
    # 正则表达式
    match = re.search(
        r"(?P<char>[\u4e00-\u9fa5]+)(?:bot排行|bot排名)",
        ev.raw_text,
    )
    if not match:
        return
    ev.regex_dict = match.groupdict()
    char = match.group("char")

    if not char:
        return

    rank_type = "伤害"
    if "评分" in char:
        rank_type = "评分"
    char = char.replace("伤害", "").replace("评分", "")

    if "练度" in char:
        im = await draw_local_total_rank(bot, ev, bot_bool=True)
    else:
        im = await draw_bot_rank_img(bot, ev, char, rank_type)

    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        await bot.send(im, at_sender)
    if isinstance(im, bytes):
        await bot.send(im)


@sv_waves_rank_all_list.on_regex("^[\u4e00-\u9fa5]+(?:总排行|总排名)(\\d+)?$", block=True)
async def send_all_rank_card(bot: Bot, ev: Event):
    # 正则表达式
    match = re.search(
        r"(?P<char>[\u4e00-\u9fa5]+)(?:总排行|总排名)(?P<pages>(\d+))?",
        ev.raw_text,
    )
    if not match:
        return
    ev.regex_dict = match.groupdict()
    char = match.group("char")
    pages = match.group("pages")

    if not char:
        return

    if pages:
        pages = int(pages)
    else:
        pages = 1

    if pages > 5:
        pages = 5
    elif pages < 1:
        pages = 1

    rank_type = "伤害"
    if "评分" in char:
        rank_type = "评分"
    char = char.replace("伤害", "").replace("评分", "")

    im = await draw_all_rank_card(bot, ev, char, rank_type, pages)

    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        await bot.send(im, at_sender)
    if isinstance(im, bytes):
        await bot.send(im)


@sv_waves_rank_total_list.on_command(("练度总排行", "练度总排名"), block=True)
async def send_total_rank_card(bot: Bot, ev: Event):
    pages = 1
    im = await draw_total_rank(bot, ev, pages)
    await bot.send(im)


@sv_waves_gacha_server_rank.on_regex(("连金榜", "连歪榜", "武器欧狗榜", "欧狗榜", "武器非酋榜", "非酋榜"), block=True)
async def send_gacha_server_rank_card(bot: Bot, ev: Event):
    """抽卡全服排行榜（基于服务器API）(支持群聊与bot用户)"""
    rank_type = ev.raw_text.strip().lower()

    user_type = ""
    if "群" in rank_type or "group" in rank_type:
        user_type = "group"
    elif "机器人" in rank_type or "bot" in rank_type:
        user_type = "bot"

    pages = re.search(r"(\d+)", rank_type)
    pages = int(pages.group(1)) if pages else 1

    for i in ["连金榜", "连歪榜", "武器欧狗榜", "欧狗榜", "武器非酋榜", "非酋榜"]:
        if i in rank_type:  # 清洗多余的参数，如："ww群武器欧狗榜" -> "武器欧狗榜"，请求总排行需要干净
            rank_type = i
            break

    im = await draw_gacha_server_rank_img(bot, ev, rank_type, pages, user_type)

    if isinstance(im, str):
        at_sender = True if ev.group_id else False
        await bot.send(im, at_sender)
    elif isinstance(im, bytes):
        await bot.send(im)


@sv_waves_matrix_rank_all.on_regex(
    r"^矩阵(群|总|bot)?排行(\d+)?$",
    block=True,
)
async def send_matrix_rank_all_card(bot: Bot, ev: Event):
    im = await draw_all_matrix_rank_card(bot, ev)
    await bot.send(im)
