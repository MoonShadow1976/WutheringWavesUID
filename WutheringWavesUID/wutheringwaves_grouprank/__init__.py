from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..utils.database.models import WavesBind
from .endless_group_rank import draw_group_rank_card
from .models import GroupRankRecord

sv_endless_group_rank = SV("ww群排行", priority=4)


@sv_endless_group_rank.on_fullmatch(("无尽排行", "无尽排名"), block=True)
async def send_endless_rank_card(bot: Bot, ev: Event):
    """处理“无尽排行”命令，显示当前赛季的群内排行。"""
    all_season_ids = await GroupRankRecord.get_all_season_ids(rank_type="endless")
    if not all_season_ids:
        return await bot.send("暂无任何赛季的排行数据")

    all_season_ids.sort(reverse=True)
    current_season_id = all_season_ids[0]

    await _handle_rank_request(bot, ev, "endless", current_season_id, 12, "海蚀无尽群排行")


@sv_endless_group_rank.on_fullmatch(("无尽排行上期", "无尽排名上期"), block=True)
async def send_previous_endless_rank_card(bot: Bot, ev: Event):
    """处理“无尽排行上期”命令，显示上一个赛季的群内排行。"""
    all_season_ids = await GroupRankRecord.get_all_season_ids(rank_type="endless")
    if not all_season_ids or len(all_season_ids) < 2:
        return await bot.send("暂无上期排行数据")

    all_season_ids.sort(reverse=True)
    previous_season_id = all_season_ids[1]

    await _handle_rank_request(bot, ev, "endless", previous_season_id, 12, "海蚀无尽群排行(上期)")


@sv_endless_group_rank.on_command("清理旧排行表", block=True)
async def clean_old_rank_tables(bot: Bot, ev: Event):
    """处理“清理旧排行表”命令，删除已弃用的旧版数据库表。仅管理员可用。"""
    if ev.user_pm > 2:
        return await bot.send("请联系管理员进行此操作")

    try:
        await GroupRankRecord.drop_old_tables()
        await bot.send("成功清理旧的排行表")
    except Exception as e:
        logger.exception(f"清理旧排行表失败: {e}")
        await bot.send(f"清理失败: {e}")


async def _handle_rank_request(bot: Bot, ev: Event, rank_type: str, season_id: int, challenge_id: int, title: str):
    """
    通用的排行请求处理函数。

    Args:
        bot: Bot 实例。
        ev: Event 实例。
        rank_type: 排行类型。
        season_id: 赛季 ID。
        challenge_id: 挑战 ID。
        title: 排行榜标题。
    """
    if not ev.group_id:
        return await bot.send("请在群聊中使用")

    try:
        # 1. 获取群内所有已绑定UID的用户
        users = await WavesBind.get_group_all_uid(ev.group_id)

        # 2. 自动处理发送者：如果发送者已绑定但未加入群排行，自动将其加入
        sender_in_list = any(user.user_id == ev.user_id for user in users) if users else False
        if not sender_in_list:
            sender_uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
            if sender_uid:
                await WavesBind.insert_waves_uid(
                    user_id=ev.user_id,
                    bot_id=ev.bot_id,
                    uid=sender_uid,
                    group_id=ev.group_id,
                )
                users = await WavesBind.get_group_all_uid(ev.group_id)  # 重新获取用户列表

        if not users:
            return await bot.send(f"[鸣潮] 群【{ev.group_id}】暂无用户。")

        # 3. 准备数据库查询所需的用户ID和游戏UID对
        user_uid_pairs = []
        for user in users:
            if user.uid:
                # 支持一个用户绑定多个游戏UID
                uids = user.uid.split("_")
                for uid in uids:
                    user_uid_pairs.append((user.user_id, uid))

        if not user_uid_pairs:
            return await bot.send(f"[鸣潮] 群【{ev.group_id}】暂无有效的用户数据。")

        # 4. 从数据库获取排行记录
        records = await GroupRankRecord.get_group_records(
            user_uid_pairs=user_uid_pairs,
            rank_type=rank_type,
            season_id=season_id,
            challenge_id=challenge_id,
        )

        # 5. 如果没有数据，发送提示信息
        if not records:
            msg = [f"[鸣潮] 群【{ev.group_id}】暂无{title}数据。"]
            msg.append("请群友使用【ww无尽】上传数据后再次查询。")
            return await bot.send("\n".join(msg))

        # 6. 绘制并发送排行榜图片
        im = await draw_group_rank_card(bot, ev, records, title)
        if isinstance(im, str):
            await bot.send(im, at_sender=bool(ev.group_id))
        elif isinstance(im, bytes):
            await bot.send(im)

    except Exception as e:
        logger.exception(f"处理排行请求失败: {e}")
        await bot.send(f"处理排行请求时发生错误: {e}")
