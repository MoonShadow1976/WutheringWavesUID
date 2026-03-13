from datetime import datetime
import time

from gsuid_core.logger import logger
from gsuid_core.segment import MessageSegment

from ..utils.api.kuro_py_api import get_base_info_overseas
from ..utils.api.model import DailyData
from ..utils.database.models import WavesPush, WavesUser
from ..utils.waves_api import waves_api
from ..wutheringwaves_config import PREFIX, WutheringWavesConfig


async def get_notice_list() -> dict[str, dict[str, dict]]:
    """获取推送列表"""
    if not WutheringWavesConfig.get_config("StaminaPush").data:
        return {}

    msg_dict = {"private_msg_dict": {}, "group_msg_dict": {}}

    user_list: list[WavesUser] = await WavesUser.get_all_push_user_list()
    logger.debug(f"[鸣潮] 推送列表: {user_list}")
    for user in user_list:
        if not user.uid or not user.cookie or user.status or not user.bot_id:
            continue

        push_data = await WavesPush.select_push_data(user.uid, user.bot_id)
        if push_data is None:
            continue

        await all_check(push_data.__dict__, msg_dict, user)

    return msg_dict


async def all_check(push_data: dict, msg_dict: dict[str, dict[str, dict]], user: WavesUser):
    # 检查条件
    mode = "resin"
    status = "push_time"

    bot_id = user.bot_id
    uid = user.uid
    token = user.cookie

    # 当前时间
    time_now = int(time.time())
    dt = datetime.strptime(push_data[f"{status}_value"], "%Y-%m-%d %H:%M:%S")
    timestamp = int(dt.timestamp())

    _push = await check(
        time_now,
        timestamp,
    )
    logger.debug(f"用户{uid} 体力提醒是否应推送:{_push}，开启状态：{push_data[f'{mode}_push']}")

    if push_data[f"{mode}_is_push"] == "on":  # 已经推送过，启动催命模式
        if WutheringWavesConfig.get_config("CrazyNotice").data:
            await WavesPush.update_data_by_uid(uid=uid, bot_id=bot_id, **{f"{mode}_is_push": "off"})
            if _push:
                refreshTimeStamp = await get_next_refresh_time(uid, token)
                if refreshTimeStamp:
                    time_refresh = int(refreshTimeStamp - (240 - push_data[f"{mode}_value"]) * 6 * 60)
                else:
                    time_refresh = timestamp

                extended_time = WutheringWavesConfig.get_config("StaminaRemindInterval").data  # 分钟
                time_repush = timestamp + int(extended_time) * 60  # 提醒时间将延长

                _push = await check(time_repush, time_refresh)  # 延长时间超过刷新时间, 需要推送

                time_out = time_repush if _push else time_refresh
                time_push = datetime.fromtimestamp(time_out)
                await WavesPush.update_data_by_uid(uid=uid, bot_id=bot_id, **{f"{status}_value": str(time_push)})
                logger.info(f"催命模式设置成功!\n当前用户{uid} 体力提醒下一次推送时间:{time_push}\n")
        return

    # 准备推送
    if _push:
        if push_data[f"{mode}_push"] == "off":
            pass
        else:
            notice = f"🌜您的结晶波片达到设定阈值啦(UID:{uid})！"
            msg_list = [
                MessageSegment.text("✅[鸣潮] 推送提醒:\n"),
                MessageSegment.text(notice),
                MessageSegment.text(f"\n🕒当前体力阈值：{push_data[f'{mode}_value']}！\n"),
                MessageSegment.text(f"\n📅请清完体力后使用[{PREFIX}每日]来更新推送时间！\n"),
            ]

            await save_push_data(mode, msg_list, push_data, msg_dict, user, True)


async def check(
    time: int,
    limit: int,
) -> bool | int:
    """超限提醒True"""
    if time >= limit:
        return True
    else:
        return False


async def get_next_refresh_time(uid: str, token: str) -> int:
    """获取下次体力刷新时间戳"""
    if not waves_api.is_net(uid):
        daily_info_res = await waves_api.get_daily_info(uid, token)
        if daily_info_res.success:
            daily_info = DailyData.model_validate(daily_info_res.data)
            return daily_info.energyData.refreshTimeStamp
    else:
        _, daily_info = await get_base_info_overseas(token, uid)
        if daily_info:
            return daily_info.energyData.refreshTimeStamp

    return 0


async def save_push_data(
    mode: str,
    msg_list: list,
    push_data: dict,
    msg_dict: dict[str, dict[str, dict]],
    user: WavesUser,
    is_need_save: bool = False,
):
    # 获取数据
    bot_id = user.bot_id
    qid = user.user_id
    uid = user.uid

    private_msgs: dict = msg_dict["private_msg_dict"]
    group_data: dict = msg_dict["group_msg_dict"]

    # on 推送到私聊
    if push_data[f"{mode}_push"] == "on":
        # 添加私聊信息
        if qid not in private_msgs:
            private_msgs[qid] = []

        private_msgs[qid].append({"bot_id": bot_id, "messages": msg_list})
    # 群号推送到群聊
    else:
        # 初始化
        gid = push_data[f"{mode}_push"]
        if gid not in group_data:
            group_data[gid] = []
        msg_list.append(MessageSegment.at(qid))
        group_data[gid].append({"bot_id": bot_id, "messages": msg_list})

    if is_need_save:
        await WavesPush.update_data_by_uid(uid=uid, bot_id=bot_id, **{f"{mode}_is_push": "on"})
