import re

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..utils.at_help import ruser_id
from ..utils.database.models import WavesBind
from ..utils.error_reply import WAVES_CODE_103
from ..utils.hint import error_reply
from .draw_char_list import draw_char_list_img

sv_waves_char_list = SV("ww角色练度统计")

_CN_DIGIT = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def _parse_page_num(s: str) -> int:
    """把 '2'/'二'/'十二'/'二十'/'二十三' 等解析为整数"""
    if not s:
        return 1
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        left, _, right = s.partition("十")
        tens = _CN_DIGIT.get(left, 1) if left else 1
        ones = _CN_DIGIT.get(right, 0) if right else 0
        return tens * 10 + ones
    return _CN_DIGIT.get(s, 1)


_SUFFIX = r"(?P<suffix>所有|全部|all|下一页|第\d+页|第[一二三四五六七八九十]+页|\d+)?"


@sv_waves_char_list.on_regex(
    r"^(\d+)?(练度统计|刷新练度统计|练度|刷新练度|角色列表|刷新角色列表)" + _SUFFIX + r"$",
    block=True,
)
async def send_char_list_msg_new(bot: Bot, ev: Event):
    match = re.search(
        r"(?P<waves_id>\d+)?"
        r"(?P<query_type>练度统计|刷新练度统计|练度|刷新练度|角色列表|刷新角色列表)" + _SUFFIX,
        ev.raw_text,
    )
    if not match:
        return

    query_waves_id = match.group("waves_id")
    query_type = match.group("query_type")
    suffix = match.group("suffix") or ""

    is_refresh = "刷新" in query_type

    is_peek = False
    if query_waves_id:
        is_peek = True
        if not query_waves_id.isdigit() or len(query_waves_id) != 9:
            return await bot.send("请输入正确的查询特征码")

    # 后缀解析：
    #   所有/全部/all     → 一页显示全部
    #   下一页            → 第2页
    #   第N页 / 第N页     → 指定页（支持中文数字）
    #   纯数字            → 指定页
    show_all = False
    index = 1
    if suffix in ("所有", "全部", "all"):
        show_all = True
    elif suffix == "下一页":
        index = 2
    elif suffix.startswith("第") and suffix.endswith("页"):
        index = _parse_page_num(suffix[1:-1])
    elif suffix.isdigit():
        index = int(suffix)
    index = max(index, 1)

    user_id = ruser_id(ev)
    user_waves_id = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    if not query_waves_id:
        query_waves_id = user_waves_id

    if not query_waves_id:
        return await bot.send(error_reply(WAVES_CODE_103))

    if not is_peek:
        await WavesBind.insert_waves_uid(user_id, ev.bot_id, query_waves_id, ev.group_id, lenth_limit=9)

    im = await draw_char_list_img(
        query_waves_id,
        ev,
        user_id,
        is_refresh,
        is_peek,
        user_waves_id,
        index,
        show_all,
    )
    return await bot.send(im)
