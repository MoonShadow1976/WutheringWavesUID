# 集成 kuro.py 的国际服登录功能
import kuro
from kuro.errors import GeetestTriggeredError, KuroError
from kuro.types import Region

from typing import Optional

from gsuid_core.logger import logger
from gsuid_core.models import Event

from .model import AccountBaseInfo, Box2, DailyData, EnergyData, LivenessData, BattlePassData
from ..database.models import WavesBind, WavesUser
from ...wutheringwaves_config import PREFIX
from ...wutheringwaves_analyzecard.user_info_utils import save_user_info

# data.mark_cookie_invalid(uid, waves_user.cookie)  # 标记为无效

async def login_overseas(
    ev: Event, email: str, password: str, geetest_data: Optional[str] = None
) -> str:
    try:
        # 创建 kuro 客户端
        client = kuro.Client(region=Region.OVERSEAS)

        # 如果有 Geetest 数据，使用 kuro.py 的内建方法
        if geetest_data:
            logger.info("使用 Geetest 验证数据进行登录")
            try:
                import json

                geetest_json = json.loads(geetest_data)  # 解析 Geetest 数据
                logger.debug(f"解析 Geetest 数据: {geetest_json}")

                mmt_result = kuro.models.MMTResult(
                    **geetest_json
                )  # 创建 MMTResult 对象
                logger.debug(f"创建 MMTResult 成功: {mmt_result}")

                login_result = await client.game_login(
                    email, password, mmt_result=mmt_result
                )

            except GeetestTriggeredError as e:
                logger.error(f"Geetest 验证触发: {e}")
                return "需要进行行为验证 (错误码: 41000)\n"
            except KuroError as e:
                logger.error(f"kuro.py Geetest 登录错误: {e}")
                logger.error(
                    f"KuroError 详细信息: retcode={e.retcode}, msg={e.msg}, api_msg={e.api_msg}"
                )
                logger.error(f"API 响应: {e.response}")
                # 检查 API 响应中的具体错误码
                api_codes = e.response.get("codes", 0)
                error_description = e.response.get("error_description", "")

                if api_codes == -4 or "校验码不通过" in error_description:
                    logger.warning("Geetest 验证码不通过，需要重新验证")
                    return "需要进行行为验证 (错误码: 41000)\n"
                elif (
                    api_codes == 10001
                    or "account or password" in error_description.lower()
                ):
                    logger.error("账号或密码错误")
                    return f"账号或密码错误: {error_description}\n"
                elif e.retcode == 0:
                    logger.warning(
                        "Geetest 验证数据可能已过期或服务器问题，需要重新验证"
                    )
                    return "需要进行行为验证 (错误码: 41000)\n"
                else:
                    return f"Geetest 验证失败: {str(e)}\n"
            except Exception as e:
                logger.error(f"kuro.py 内建登录失败: {e}")
                # 回退到原始方法
                return f"Geetest 验证失败: {str(e)}.\n"
        else:
            # 正常登录
            try:
                login_result = await client.game_login(email, password)
            except GeetestTriggeredError as e:
                logger.info(f"触发 Geetest 验证: {e}")
                return "需要进行行为验证 (错误码: 41000)\n"
            except KuroError as e:
                logger.info(f"kuro.py 错误: {e}")
                logger.info(
                    f"KuroError 详细信息: retcode={e.retcode}, msg={e.msg}, api_msg={e.api_msg}"
                )
                logger.info(f"API 响应: {e.response}")
                # 检查 API 响应中的具体错误码
                api_codes = e.response.get("codes", 0)
                error_description = e.response.get("error_description", "")

                if (
                    api_codes == 10001
                    or "account or password" in error_description.lower()
                ):
                    logger.error("账号或密码错误")
                    return f"账号或密码错误: {error_description}\n"
                elif e.retcode == 0:  # Unknown error
                    return "需要进行行为验证 (错误码: 41000)\n"
                else:
                    return f"登录失败: {str(e)}\n"
            except Exception as e:
                logger.info(f"正常登录失败，可能需要 Geetest 验证: {e}")
                # 检查是否为需要 Geetest 验证的错误
                error_str = str(e).lower()
                if any(
                    keyword in error_str
                    for keyword in [
                        "41000",
                        "行為驗證",
                        "行为验证",
                        "unknown error",
                        "captcha",
                        "verification",
                    ]
                ):
                    return "需要进行行为验证 (错误码: 41000)\n"
                else:
                    return f"登录失败: {str(e)}\n"

        # 登录成功，继续处理
        logger.debug(f"国际服登录成功: \n{login_result}")

        # 获取游戏 token
        token_result = await client.get_game_token(login_result.code)
        logger.debug(f"获取游戏 token 成功: {token_result}")

        # 生成 OAuth code
        oauth_code = await client.generate_oauth_code(token_result.access_token)
        logger.debug(f"生成 OAuth code 成功: {oauth_code}")

        # 获取玩家信息以确定 UID
        player_infos = await client.get_player_info(oauth_code)
        logger.info(f"获取玩家信息成功: {len(player_infos)} 个角色")

    except Exception as e:
        logger.error(f"kuro.py 登录失败: {e}")
        # 检查是否为需要 Geetest 验证的错误，如果是则重新抛出
        error_str = str(e).lower()
        if any(
            keyword in error_str
            for keyword in [
                "41000",
                "行為驗證",
                "行为验证",
                "unknown error",
                "captcha",
                "verification",
            ]
        ):
            return "需要进行行为验证 (错误码: 41000)\n"
        else:
            return f"登录失败: {str(e)}\n"

    for region, player_info in player_infos.items():
        logger.debug(f"角色區域: {region}, 角色信息: {player_info}")
        if not player_info:
            continue

        uid = str(player_info.uid)  # 使用 uid 字段

        # 國際服登入成功，存儲用戶數據
        # 為國際服創建/更新 WavesUser 記錄

        # 檢查是否已存在用戶
        existing_user = await WavesUser.get_user_by_attr(
            ev.user_id, ev.bot_id, "uid", uid
        )

        if existing_user:
            # 更新現有用戶
            await WavesUser.update_data_by_data(
                select_data={
                    "user_id": ev.user_id,
                    "bot_id": ev.bot_id,
                    "uid": uid,
                },
                update_data={
                    "cookie": token_result.access_token,
                    "platform": region,
                    "status": "",
                },
            )
            logger.info(f"WavesUser 更新成功: UID {uid}")
        else:
            # 創建新用戶
            await WavesUser.insert_data(
                user_id=ev.user_id,
                bot_id=ev.bot_id,
                cookie=token_result.access_token,
                uid=uid,
                platform=region,
                status="",
            )
            logger.info(f"WavesUser 創建成功: UID {uid}")

        # 更新綁定信息
        await WavesBind.insert_waves_uid(
            ev.user_id,
            ev.bot_id,
            uid,
            ev.group_id,
            lenth_limit=9,
        )

        # 保存用户信息到本地
        await save_user_info(uid, player_info.name, level=player_info.level)

    return f"[鸣潮] 国际服登录成功!\n现在可以使用：\n [{PREFIX}查看]查看您登录的所有UID\n [{PREFIX}切换]在您登录的UID之间切换\n"


async def get_base_info_overseas(ck:str, uid: str) -> tuple[None, None] | tuple[AccountBaseInfo, DailyData]:
    """获取国际服账户基础信息"""
    client = kuro.Client(region=Region.OVERSEAS)

    waves_user= await WavesUser.select_data_by_cookie_and_uid(cookie=ck, uid=uid)
    if not waves_user:
        return None, None
    try:
        oauth_code = await client.generate_oauth_code(ck)

        role_info = await client.get_player_role(oauth_code, int(uid), waves_user.platform)
        basic = role_info.basic
        battle_pass = role_info.battle_pass
        if not basic or not battle_pass:
            return None, None
    except Exception as e:
        logger.error(f"获取国际服用户信息失败: {e}")
        return None, None
    
    # 保存用户信息到本地
    await save_user_info(uid, basic.name, level=basic.level, worldLevel=basic.world_level)

    BoxList = []
    for box_type, box_count in basic.chests.items():
        name_list = {
            "1": "基准奇藏箱",
            "2": "朴素奇藏箱",
            "3": "精密奇藏箱",
            "4": "辉光奇藏箱",
        }
        BoxList.append(Box2(name=name_list.get(box_type, "未知宝箱"), num=box_count))
    
    TidalHeritagesList = []
    for heritage_type, heritage_count in basic.tidal_heritages.items():
        name_list = {
            "1": "潮汐之遗绿",
            "2": "潮汐之遗紫",
            "3": "潮汐之遗金",
        }
        TidalHeritagesList.append(Box2(name=name_list.get(heritage_type, "未知潮汐之遗"), num=heritage_count))
    
    baseInfo = AccountBaseInfo(
        name=basic.name,
        id=int(uid),
        activeDays=basic.active_days,
        level=basic.level,
        worldLevel=basic.world_level,
        roleNum=basic.character_count,
        treasureBoxList=BoxList,
        tidalHeritagesList=TidalHeritagesList,
        weeklyInstCount=basic.weekly_challenge,
        weeklyInstCountLimit=3,
        storeEnergy=basic.refined_waveplates,
        storeEnergyLimit=480,
        rougeScore=0,
        rougeScoreLimit=6000,
    )

    dailyData = DailyData(
        gameId=0, # [每日]默认不使用
        userId=0, # 同
        serverId="0", # 同
        roleName=basic.name,
        roleId=uid,
        signInTxt="国际服用户", # 同
        hasSignIn=False,
        energyData=EnergyData(
            name="结晶波片",img="",
            refreshTimeStamp=int(basic.waveplates_replenish_time.timestamp()),
            cur=basic.waveplates,
            total=basic.max_waveplates,
        ),
        livenessData=LivenessData(
            name="活跃度",img="",
            cur=basic.activity_points,
            total=basic.max_activity_points,
        ),
        battlePassData=[BattlePassData(
            name="电台",
            cur=battle_pass.level,
            total=70,
        )]
    )

    return baseInfo, dailyData
