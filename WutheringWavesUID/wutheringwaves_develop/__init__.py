import re

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..utils.name_convert import CHAR_NAME_PATTERN, get_event_command_text
from ..wutheringwaves_develop.develop import calc_develop_cost, mock_calc_develop_cost

role_develop = SV("waves角色培养")


@role_develop.on_regex(
    rf"(?P<develop_list>({CHAR_NAME_PATTERN})(\s+{CHAR_NAME_PATTERN})*?)\s*(材料|养成|培养|培养成本)",
    block=True,
)
async def calc_develop(bot: Bot, ev: Event):
    match = re.search(
        rf"(?P<develop_list>({CHAR_NAME_PATTERN})(\s+{CHAR_NAME_PATTERN})*?)\s*(材料|养成|培养|培养成本)",
        get_event_command_text(ev),
    )
    if not match:
        return

    develop_list_str = match.group("develop_list")
    develop_list = develop_list_str.split()
    logger.info(f"养成列表: {develop_list}")

    develop_cost = await calc_develop_cost(ev, develop_list)
    if isinstance(develop_cost, bytes):
        return await bot.send(develop_cost)
    else:
        logger.warning(f"用户养成返回错误，使用默认。错误提示: {develop_cost}")
        return await bot.send(await mock_calc_develop_cost(ev, develop_list))
