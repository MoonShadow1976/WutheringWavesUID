from typing import Dict

from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsBoolConfig,
    GsDictConfig,
    GsIntConfig,
    GsListConfig,
    GsListStrConfig,
    GsStrConfig,
)

CONFIG_DEFAULT: Dict[str, GSC] = {
    "RedisFromUrl": GsStrConfig(
        "Redis连接配置",
        "Redis连接配置",
        "redis://127.0.0.1:6379/0",
    ),
    "IsRedisCluster": GsBoolConfig(
        "Redis集群开关",
        "Redis集群开关",
        False,
    ),
    "StartServerRedisLoad": GsBoolConfig(
        "开启后，在启动GsCore时，redis加载排行数据",
        "开启后，在启动GsCore时，redis加载排行数据",
        False,
    ),
    "WavesAnnGroups": GsDictConfig(
        "推送公告群组",
        "鸣潮公告推送群组",
        {},
    ),
    "WavesAnnNewIds": GsListConfig(
        "推送公告ID",
        "鸣潮公告推送ID列表",
        [],
    ),
    "WavesRankUseTokenGroup": GsListStrConfig(
        "有token才能进排行，群管理可设置",
        "有token才能进排行，群管理可设置",
        [],
    ),
    "WavesRankNoLimitGroup": GsListStrConfig(
        "无限制进排行，群管理可设置",
        "无限制进排行，群管理可设置",
        [],
    ),
    "SignTime": GsListStrConfig(
        "每晚签到时间设置",
        "每晚库街区签到时间设置（时，分）",
        ["0", "10"],
    ),
    "SchedSignin": GsBoolConfig(
        "定时签到",
        "开启后每晚00:10将开始自动签到任务",
        True,
    ),
    "BBSSchedSignin": GsBoolConfig(
        "定时库街区每日任务",
        "开启后每晚00:20将开始自动库街区每日任务",
        True,
    ),
    "PrivateSignReport": GsBoolConfig(
        "签到私聊报告",
        "关闭后将不再给任何人推送当天签到任务完成情况",
        False,
    ),
    "GroupSignReport": GsBoolConfig(
        "签到群组报告",
        "关闭后将不再给任何群推送当天签到任务完成情况",
        True,
    ),
    "GroupSignReportPic": GsBoolConfig(
        "签到群组图片报告",
        "签到以图片形式报告",
        False,
    ),
    "SigninMaster": GsBoolConfig(
        "全部开启签到",
        "开启后自动帮登录的人签到",
        False,
    ),
    "SigninConcurrentNum": GsIntConfig("自动签到并发数量", "自动签到并发数量", 5, 50),
    "CrazyNotice": GsBoolConfig("催命模式", "开启后当达到推送阈值将会一直推送", False),
    "WavesGuideProvideNew": GsStrConfig(
        "角色攻略图提供方",
        "使用ww角色攻略时选择的提供方",
        "金铃子攻略组",
        options=["all", "金铃子攻略组", "結星", "Moealkyne"],
    ),
    "WavesLoginUrl": GsStrConfig(
        "鸣潮登录url",
        "用于设置WutheringWavesUID登录界面的配置",
        "",
    ),
    "WavesLoginUrlSelf": GsBoolConfig(
        "强制【鸣潮登录url】为自己的域名",
        "强制【鸣潮登录url】为自己的域名",
        False,
    ),
    "WavesQRLogin": GsBoolConfig(
        "开启后，登录链接变成二维码",
        "开启后，登录链接变成二维码",
        False,
    ),
    "WavesLoginForward": GsBoolConfig(
        "开启后，登录链接变为转发消息",
        "开启后，登录链接变为转发消息",
        False,
    ),
    "WavesOnlySelfCk": GsBoolConfig(
        "所有查询使用自己的ck",
        "所有查询使用自己的ck",
        False,
    ),
    "BotRank": GsBoolConfig(
        "bot排行",
        "bot排行",
        False,
    ),
    "CardUseOptions": GsStrConfig(
        "排行面板数据启用规则（重启生效）",
        "排行面板数据启用规则",
        "不使用缓存",
        options=["不使用缓存", "redis缓存", "内存缓存"],
    ),
    "QQPicCache": GsBoolConfig(
        "排行榜qq头像缓存开关",
        "排行榜qq头像缓存开关",
        False,
    ),
    "RankUseToken": GsBoolConfig(
        "有token才能进排行",
        "有token才能进排行",
        False,
    ),
    "DelInvalidCookie": GsBoolConfig(
        "每天定时删除无效token",
        "每天定时删除无效token",
        False,
    ),
    "AnnMinuteCheck": GsIntConfig(
        "公告推送时间检测（单位min）", "公告推送时间检测（单位min）", 10, 60
    ),
    "RefreshNotify": GsBoolConfig(
        "刷新面板通知文案",
        "刷新面板通知文案",
        True,
    ),
    "HideUid": GsBoolConfig(
        "隐藏uid",
        "隐藏uid",
        False,
    ),
    "MaxBindNum": GsIntConfig(
        "绑定特征码限制数量（未登录）", "绑定特征码限制数量（未登录）", 2, 100
    ),
    "WavesToken": GsStrConfig(
        "鸣潮全排行token",
        "鸣潮全排行token",
        "",
    ),
}
