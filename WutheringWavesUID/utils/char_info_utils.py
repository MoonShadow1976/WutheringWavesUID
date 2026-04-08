from collections.abc import Generator
import json
from typing import Any

import aiofiles
from gsuid_core.logger import logger
import httpx

from ..utils.api.model import RoleDetailData
from ..utils.api.wwapi import GET_ROLE_DETAIL_URL, RoleDetailResponse
from ..wutheringwaves_config.wutheringwaves_config import WutheringWavesConfig
from .resource.RESOURCE_PATH import PLAYER_PATH


async def get_all_role_detail_info_list(
    uid: str,
) -> Generator[RoleDetailData, Any, None] | None:
    path = PLAYER_PATH / uid / "rawData.json"
    if not path.exists():
        return None
    try:
        async with aiofiles.open(path, encoding="utf-8") as f:
            player_data = json.loads(await f.read())
    except Exception as e:
        logger.exception(f"get role detail info failed {path}:", e)
        path.unlink(missing_ok=True)
        return None

    return iter(RoleDetailData(**r) for r in player_data)


async def get_all_role_detail_info(uid: str) -> dict[str, RoleDetailData] | None:
    _all = await get_all_role_detail_info_list(uid)
    if not _all:
        return None
    return {r.role.roleName: r for r in _all}


async def get_all_roleid_detail_info(
    uid: str,
) -> dict[str, RoleDetailData] | None:
    _all = await get_all_role_detail_info_list(uid)
    if not _all:
        return None
    return {str(r.role.roleId): r for r in _all}


async def get_all_roleid_detail_info_int(
    uid: str,
) -> dict[int, RoleDetailData] | None:
    _all = await get_all_role_detail_info_list(uid)
    if not _all:
        return None
    return {r.role.roleId: r for r in _all}


async def get_role_detail_online(waves_id: str | int) -> RoleDetailResponse | None:
    WavesToken = WutheringWavesConfig.get_config("WavesToken").data

    if not WavesToken:
        return

    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                GET_ROLE_DETAIL_URL,
                json={"waves_id": str(waves_id)},
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {WavesToken}",
                },
                timeout=httpx.Timeout(10),
            )
            # logger.debug(f"获取角色细节: {res.text}")
            if res.status_code == 200:
                return RoleDetailResponse.model_validate(res.json())
        except Exception as e:
            logger.exception(f"获取角色细节失败: {e}")


async def get_roleid_detail_online(
    uid: str,
) -> dict[str, RoleDetailData] | None:
    result = await get_role_detail_online(uid)
    if not result or not result.data.data:
        return None
    _data = [RoleDetailData(**r) for r in result.data.data]
    return {str(r.role.roleId): r for r in _data}
