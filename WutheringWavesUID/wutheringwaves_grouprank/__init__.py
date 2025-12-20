from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..utils.database.models import WavesBind
from .draw_group_rank_card import draw_group_rank_card
from .models import GroupRankRecord

# 注册服务
sv_endless_group_rank = SV("ww无尽群排行", priority=4)

# --- 命令处理 ---


@sv_endless_group_rank.on_regex(r"^无尽(?:排行|排名)$", block=True)
async def send_endless_rank_card(bot: Bot, ev: Event):
    """
    无尽排行命令
    """
    await _handle_rank_request(bot, ev, "endless", 12, "海蚀无尽群排行")


@sv_endless_group_rank.on_command("清理无尽群排行", block=True)
async def clean_rank_data(bot: Bot, ev: Event):
    """
    清理排行重复数据
    """
    if ev.user_pm > 2:
        return await bot.send("请联系管理员进行清理")

    try:
        count = await GroupRankRecord.remove_duplicates()
        await bot.send(f"清理完成，共清理 {count} 条重复数据")
    except Exception as e:
        logger.exception(f"清理排行数据失败: {e}")
        await bot.send(f"清理失败: {e}")


async def _handle_rank_request(bot: Bot, ev: Event, rank_type: str, challenge_id: int, title: str):
    """
    通用排行请求处理
    """
    if not ev.group_id:
        return await bot.send("请在群聊中使用")

    try:
        # 获取群内用户
        users = await WavesBind.get_group_all_uid(ev.group_id)

        # 检查发送者是否在列表中，如果不在且已绑定，则自动添加
        sender_in_list = False
        if users:
            for user in users:
                if user.user_id == ev.user_id:
                    sender_in_list = True
                    break

        if not sender_in_list:
            # 尝试获取发送者的绑定信息
            sender_uid = await WavesBind.get_uid_by_game(ev.user_id, ev.bot_id)
            if sender_uid:
                # 自动关联到当前群
                await WavesBind.insert_waves_uid(user_id=ev.user_id, bot_id=ev.bot_id, uid=sender_uid, group_id=ev.group_id)
                # 重新获取群内用户
                users = await WavesBind.get_group_all_uid(ev.group_id)

        if not users:
            return await bot.send(f"[鸣潮] 群【{ev.group_id}】暂无登录用户。")

        # 准备查询条件
        user_uid_pairs = []
        for user in users:
            if user.uid:
                uids = user.uid.split("_")
                for uid in uids:
                    user_uid_pairs.append((user.user_id, uid))

        if not user_uid_pairs:
            return await bot.send(f"[鸣潮] 群【{ev.group_id}】暂无有效的用户数据。")

        # 获取数据
        records = await GroupRankRecord.get_group_records(
            user_uid_pairs=user_uid_pairs, rank_type=rank_type, challenge_id=challenge_id
        )

        if not records:
            msg = [f"[鸣潮] 群【{ev.group_id}】暂无{title}数据。"]
            msg.append("请群友使用【ww无尽】上传数据后再次查询。")
            return await bot.send("\n".join(msg))

        # 绘制卡片
        im = await draw_group_rank_card(bot, ev, records, title)

        # 发送结果
        if isinstance(im, str):
            at_sender = True if ev.group_id else False
            await bot.send(im, at_sender)
        elif isinstance(im, bytes):
            await bot.send(im)

    except Exception as e:
        logger.exception(f"处理排行请求失败: {e}")
        await bot.send(f"处理排行请求时发生错误: {e}")
