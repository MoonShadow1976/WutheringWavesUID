import json

from pathlib import Path
from dataclasses import field, dataclass
from typing import Any, Dict, List

from gsuid_core.logger import logger

from ..utils.util import send_master_info
from ..utils.ascension.weapon import get_weapon_detail
from ..wutheringwaves_analyzecard.user_info_utils import save_user_info
from ..utils.ascension.echo import get_echo_model
from ..utils.ascension.model import EchoModel
from ..utils.api.model import AccountBaseInfo as BaseInfo

from .detail_json import m_id2monsterId_strange, main_first_props, main_second_props, sub_props


TEXT_PATH = Path(__file__).parent




@dataclass
class RoleInfo:
    """角色信息"""

    role_id: int
    level: int
    breach: int
    resonant_chain_group_index: int  # 角色共鸣链
    exp: int
    skills: List[Dict[str, Any]] = field(default_factory=list)  # 技能數據
    skill_node_state: List[Dict[str, Any]] = field(default_factory=list)  # 技能節點狀態


@dataclass
class WeaponInfo:
    """武器信息"""

    weapon_id: int
    level: int
    breach: int  # 武器突破阶级
    reson_level: int  # 武器精炼
    exp: int
    role_id: int = 0  # 裝備該武器的角色ID


@dataclass
class PhantomInfo:
    """聲骸信息"""

    phantom_incr_list: List[Dict[str, Any]]


def get_breach(level: int):
    if level <= 20:
        breach = 0
    elif level <= 40:
        breach = 1
    elif level <= 50:
        breach = 2
    elif level <= 60:
        breach = 3
    elif level <= 70:
        breach = 4
    elif level <= 80:
        breach = 5
    elif level <= 90:
        breach = 6
    else:
        breach = 0
    return breach


class PcapDataParser:
    """PCAP 數據解析器"""

    def __init__(self):
        self.account_info = BaseInfo
        self.role_data = {}
        self.weapon_data = {}
        self.phantom_data = {}
        self.phantom_index = {}  # 聲骸映射表 {phantom_id: phantom_name}
        self.property_index = {}  # 屬性映射表 {property_id: property_info}

    async def save_pcap_data(self, waves_data: dict):
        """保存 pcap 解析的數據"""
        try:
            # 創建用戶數據目錄
            user_data_dir = Path("data/pcap_data") / str(self.account_info.id)
            user_data_dir.mkdir(parents=True, exist_ok=True)

            # 保存數據到 JSON 文件
            data_file = user_data_dir / "latest_data.json"
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(waves_data, f, ensure_ascii=False, indent=2)

            logger.success(f"pcap 數據已保存到：{data_file}")

        except Exception as e:
            logger.error(f"保存 pcap 數據失敗: {e}")

    def _load_phantom_index(self):
        """載入聲骸索引"""
        try:

            # 嘗試多個可能的路徑
            possible_paths = [
                "zh-Hant/Phantom",
                "../zh-Hant/Phantom",
                "../../zh-Hant/Phantom",
                "WutheringWavesUID/zh-Hant/Phantom",
                "../WutheringWavesUID/zh-Hant/Phantom",
            ]

            phantom_dir = None
            for path in possible_paths:
                test_path = TEXT_PATH / path
                if test_path.exists():
                    phantom_dir = test_path
                    break

            if phantom_dir:
                logger.info(f"✅ 找到聲骸目錄: {phantom_dir}")
                phantom_count = 0

                for phantom_file in phantom_dir.glob("*.json"):
                    try:
                        with open(phantom_file, "r", encoding="utf-8") as f:
                            phantom_data = json.load(f)
                            phantom_id = phantom_data.get("id")
                            monsterId = phantom_data.get("monsterId")

                            if phantom_id:
                                self.phantom_index[phantom_id] = monsterId
                                phantom_count += 1

                    except Exception as e:
                        logger.error(f"載入聲骸失敗: {phantom_file.name}, {e}")

                logger.info(f"✅ 載入 {phantom_count} 個聲骸")
            else:
                logger.error("❌ 找不到聲骸目錄")
        except Exception as e:
            logger.error(f"載入聲骸索引失敗: {e}")

    def _load_property_index(self):
        """載入屬性索引"""
        try:

            # 嘗試多個可能的路徑
            possible_paths = [
                "zh-Hant/LocalizationIndex/PropertyIndexs.json",
                "../zh-Hant/LocalizationIndex/PropertyIndexs.json",
                "../../zh-Hant/LocalizationIndex/PropertyIndexs.json",
                "WutheringWavesUID/zh-Hant/LocalizationIndex/PropertyIndexs.json",
                "../WutheringWavesUID/zh-Hant/LocalizationIndex/PropertyIndexs.json",
            ]

            property_file = None
            for path in possible_paths:
                test_path = TEXT_PATH / path
                if test_path.exists():
                    property_file = test_path
                    break

            if property_file:
                logger.info(f"✅ 找到屬性索引文件: {property_file}")
                with open(property_file, "r", encoding="utf-8") as f:
                    properties = json.load(f)
                    for prop in properties:
                        self.property_index[prop["id"]] = {
                            "name": prop.get("name", "缺失名稱"),
                            "isPercent": prop.get("isPercent", False),
                            "key": prop.get("key", ""),
                        }
                logger.info(f"✅ 載入 {len(self.property_index)} 個屬性")
            else:
                logger.error("❌ 找不到屬性索引文件")
        except Exception as e:
            logger.error(f"載入屬性索引失敗: {e}")

    async def parse_pcap_data(self, pcap_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析 PCAP 數據

        Args:
            pcap_data: 從 API 獲取的原始數據

        Returns:
            解析後的角色詳細數據列表
        """
        # 記錄原始數據結構
        if isinstance(pcap_data, dict):
            logger.info(f"PCAP 數據鍵: {list(pcap_data.keys())}")
        elif isinstance(pcap_data, list):
            logger.info(f"PCAP 數據是列表格式，包含 {len(pcap_data)} 個項目")
            # 如果直接是角色詳細數據列表，直接返回
            return pcap_data
        else:
            logger.warning(f"未知的 PCAP 數據格式: {type(pcap_data)}")
            return []

        try:
            # 檢查是否有已處理的角色詳細數據 -- 刷新面板用
            if "role_detail_list" in pcap_data:
                role_detail_list = pcap_data["role_detail_list"]
                logger.info(
                    f"直接使用已處理的角色詳細數據，共 {len(role_detail_list)} 個角色"
                )
                return role_detail_list

            logger.info("🔧 初始化 PcapDataParser...")
            # self._load_phantom_index()
            # self._load_property_index()
            logger.info(
                f"🔧 PcapDataParser 初始化完成，載入了 {len(self.phantom_index)} 个聲骸映射，{len(self.property_index)} 個属性映射"
            )

            # 檢查是否是 Wuthery API 響應格式
            if "data" in pcap_data and isinstance(pcap_data["data"], dict):
                data = pcap_data["data"]
                logger.debug(f"找到 data 字段，鍵: {list(data.keys())}")
            else:
                logger.debug(
                    f"沒有找到 data 字段或 data 不是字典，pcap_data 鍵: {list(pcap_data.keys())}"
                )
                # 直接使用 pcap_data 作為數據源
                data = pcap_data

            # 提取用户數據
            if "BasicInfoNotify" in data and "id" in data["BasicInfoNotify"]:
                self._extract_base_info_data_from_wuthery(data["BasicInfoNotify"])
            else:
                logger.error("數據中沒有 BasicInfoNotify")
                return []

            # 提取用户成就數據
            if "AchievementInfoResponse" in data:
                self._extract_achievement_info_data_from_wuthery(data["AchievementInfoResponse"])
            else:
                logger.warning("數據中沒有 AchievementInfoResponse")

            logger.info(f"從 Wuthery API 提取到用户信息：{self.account_info}")

            # 提取角色數據
            if (
                "PbGetRoleListNotify" in data
                and "role_list" in data["PbGetRoleListNotify"]
            ):
                self._extract_role_data_from_wuthery(
                    data["PbGetRoleListNotify"]["role_list"]
                )
                logger.info(f"從 Wuthery API 提取到 {len(self.role_data)} 個角色")
            else:
                logger.error("數據中沒有 PbGetRoleListNotify 或 role_list")

            # 提取武器數據
            if "WeaponItemResponse" in data:
                logger.debug(
                    f"找到 WeaponItemResponse，鍵: {list(data['WeaponItemResponse'].keys())}"
                )
                if "weapon_item_list" in data["WeaponItemResponse"]:
                    weapon_list = data["WeaponItemResponse"]["weapon_item_list"]
                    logger.debug(f"武器列表長度: {len(weapon_list)}")
                    self._extract_weapon_data_from_wuthery(weapon_list)
                    logger.info(f"從 Wuthery API 提取到 {len(self.weapon_data)} 個武器")
                else:
                    logger.warning("WeaponItemResponse 中沒有 weapon_item_list")
            else:
                logger.warning("數據中沒有 WeaponItemResponse")

            # 提取聲骸數據
            if "PhantomItemResponse" in data:
                logger.debug(
                    f"找到 PhantomItemResponse，鍵: {list(data['PhantomItemResponse'].keys())}"
                )
                self._extract_phantom_data_from_wuthery(data["PhantomItemResponse"])
                logger.info(
                    f"從 Wuthery API 提取到 {len(self.phantom_data)} 個角色的聲骸數據"
                )
            else:
                logger.warning("數據中沒有 PhantomItemResponse")

            # 構建角色詳細數據
            role_detail_list = await self._build_role_detail_list()

            logger.info(f"Wuthery API 數據解析完成，共 {len(role_detail_list)} 個角色")

            if role_detail_list:
                waves_data_dict = {"role_detail_list": role_detail_list}
                await self.save_pcap_data(waves_data_dict)
                # 保存用户基本信息
                await save_user_info(
                    uid=str(self.account_info.id),
                    name=self.account_info.name[:7],
                    level=self.account_info.level if self.account_info.level else 0,
                    worldLevel=self.account_info.worldLevel if self.account_info.worldLevel else 0,
                    achievementCount=self.account_info.achievementCount if self.account_info.achievementCount else 0,
                    achievementStar=self.account_info.achievementStar if self.account_info.achievementStar else 0,
                )

            return role_detail_list

        except Exception as e:
            logger.exception("PCAP 數據解析失敗", e)
            return []

    def _extract_base_info_data_from_wuthery(self, base_info: Dict[str, Any]):
        """從 Wuthery API 格式提取用户基本數據"""
        try:
            uid = base_info.get("id")
            if not uid:
                logger.warning("從 Wuthery API 提取用户id失敗")
                return

            # 初始化默认值
            level = 0
            name = "获取失败"
            world_level = 0

            # 遍历属性列表提取所需值
            attributes = base_info.get("attributes", [])
            for attribute in attributes:
                key = attribute.get("key")
                if key == 0:  # level
                    level = attribute.get("int32_value", 0)
                elif key == 7:  # name
                    name = attribute.get("string_value", "获取失败")
                elif key == 11:  # worldLevel
                    world_level = attribute.get("int32_value", 0)

            self.account_info = BaseInfo(
                id=uid, name=name, level=level, worldLevel=world_level
            )

        except Exception as e:
            logger.exception("從 Wuthery API 提取角色數據失敗", e)

    def _extract_achievement_info_data_from_wuthery(self, achievement_info: Dict[str, Any]):
        """從 Wuthery API 格式提取用户成就數據"""
        try:
            achievement_count = achievement_info.get("finished_achievement_num", 0)
            achievement_star = achievement_info.get("achievement_finished_star", 0)

            # 更新用户基本信息中的成就數據
            self.account_info.achievementCount = achievement_count
            self.account_info.achievementStar = achievement_star

            logger.debug(
                f"提取用户成就數據: 已达成成就 {achievement_count} 个, 成就星数 {achievement_star}"
            )

        except Exception as e:
            logger.exception("從 Wuthery API 提取用户成就數據失敗", e)

    def _extract_role_data_from_wuthery(self, role_list: List[Dict[str, Any]]):
        """從 Wuthery API 格式提取角色數據"""
        try:
            for role in role_list:
                role_id = role.get("role_id")
                if not role_id:
                    continue

                # 提取角色基本信息
                level = role.get("level", 1)
                exp = role.get("exp", 0)
                breakthrough = role.get("breakthrough", 0)  # 直接使用突破等級
                resonant_chain_group_index = role.get("resonant_chain_group_index", 0)

                # 提取技能數據
                skills = role.get("skills", [])
                skill_node_state = role.get("skill_node_state", [])

                self.role_data[role_id] = RoleInfo(
                    role_id=role_id,
                    level=level,
                    breach=breakthrough,  # 使用實際的突破等級
                    exp=exp,
                    resonant_chain_group_index=resonant_chain_group_index,
                    skills=skills,
                    skill_node_state=skill_node_state,
                )

                logger.debug(
                    f"提取角色數據: ID {role_id}, 等級 {level}, 突破 {breakthrough}, 共鳴鏈 {resonant_chain_group_index}"
                )

        except Exception as e:
            logger.exception("從 Wuthery API 提取角色數據失敗", e)

    def _extract_weapon_data_from_wuthery(self, weapon_list: List[Dict[str, Any]]):
        """從 Wuthery API 格式提取武器數據"""
        try:
            logger.debug(f"開始提取武器數據，武器列表長度: {len(weapon_list)}")
            extracted_count = 0

            for weapon in weapon_list:
                weapon_id = weapon.get("id")
                if not weapon_id:
                    continue

                level = weapon.get("weapon_level", 1)
                breach = weapon.get("weapon_breach", 0)
                exp = weapon.get("weapon_exp", 0)
                reson_level = weapon.get("weapon_reson_level", 1)  # 精煉等級
                role_id = weapon.get("role_id", 0)  # 裝備該武器的角色ID
                incr_id = weapon.get("incr_id", 0)  # 唯一標識符

                # 使用 incr_id 作為唯一鍵，避免重複武器ID的問題
                unique_key = f"{weapon_id}_{incr_id}" if incr_id > 0 else weapon_id

                self.weapon_data[unique_key] = WeaponInfo(
                    weapon_id=weapon_id,
                    level=level,
                    breach=breach,
                    exp=exp,
                    reson_level=reson_level,
                    role_id=role_id,
                )

                extracted_count += 1
                logger.debug(
                    f"提取武器數據: ID {weapon_id}, 精炼 {reson_level}, 等級 {level}, 突破 {breach}, 角色 {role_id}, 唯一鍵 {unique_key}"
                )

            logger.debug(f"武器數據提取完成，共提取 {extracted_count} 個武器")

        except Exception as e:
            logger.exception("從 Wuthery API 提取武器數據失敗", e)

    def _extract_phantom_data_from_wuthery(self, phantom_data: Dict[str, Any]):
        """從 Wuthery API 格式提取聲骸數據"""
        try:
            # 提取裝備信息
            equip_info = phantom_data.get("equip_info", [])
            phantom_item_list = phantom_data.get("phantom_item_list", [])

            # 處理裝備信息
            for equip in equip_info:
                role_id = equip.get("role_id", 0)
                phantom_item_incr_id = equip.get("phantom_item_incr_id", [])

                if role_id and phantom_item_incr_id:
                    # 查找對應的聲骸數據
                    phantom_incr_list = []
                    for incr_id in (
                        phantom_item_incr_id if len(phantom_item_incr_id) <= 5 else []
                    ):  # 不处理0, 超限不处理
                        if incr_id > 0:  # 只處理有效的聲骸ID
                            for phantom_item in phantom_item_list:
                                if phantom_item.get("incr_id") == incr_id:
                                    phantom_incr_list.append(phantom_item)
                                    break

                    if phantom_incr_list:
                        self.phantom_data[role_id] = PhantomInfo(
                            phantom_incr_list=phantom_incr_list,
                        )
                        logger.debug(
                            f"原始数据:{role_id}-{phantom_item_incr_id}，处理完的数据有 {len(phantom_incr_list)} 个"
                        )

        except Exception as e:
            logger.exception("從 Wuthery API 提取聲骸數據失敗", e)

    async def _build_role_detail_list(self) -> List[Dict[str, Any]]:
        """構建角色詳細數據列表"""
        role_detail_list = []

        for role_id, role_info in self.role_data.items():
            try:
                # 獲取角色名稱
                role = await self._get_role(role_id)
                if isinstance(role, str):
                    continue

                # 構建角色數據
                role_detail = {
                    "level": role_info.level,
                    "role": {
                        "acronym": role.role.acronym,
                        "attributeId": role.role.attributeId,
                        "attributeName": role.role.attributeName,
                        "breach": get_breach(role_info.level),
                        "chainUnlockNum": role_info.resonant_chain_group_index,
                        "isMainRole": False,  # 假设需要一个主角色标识（用户没有提供，可以设置默认值或动态获取）
                        "level": role_info.level,
                        "roleIconUrl": role.role.roleIconUrl,
                        "roleId": role.role.roleId,
                        "roleName": role.role.roleName,
                        "rolePicUrl": role.role.rolePicUrl,
                        "starLevel": role.role.starLevel,
                        "weaponTypeId": role.role.weaponTypeId,
                        "weaponTypeName": role.role.weaponTypeName,
                    },
                    "chainList": self._build_chain_list(role_info, role),
                    "skillList": self._build_skill_list(role_info, role),
                    "weaponData": self._build_weapon_data(role_id, role),
                    "phantomData": await self._build_phantom_data(role_id, role),
                }

                role_detail_list.append(role_detail)
                logger.debug(f"構建角色詳細數據: {role.role.roleName} (ID: {role_id})")

            except Exception as e:
                logger.exception(f"構建角色 {role_id} 詳細數據失敗", e)

        return role_detail_list

    async def _get_role(self, role_id: int):
        """获取角色模版"""
        try:
            from ..wutheringwaves_charinfo.draw_char_card import (
                generate_online_role_detail,
            )

            # char_id = "1506" # 菲比..utils\map\detail_json\char\1506.json
            result = await generate_online_role_detail(str(role_id))
            if not result:
                logger.warning("[鸣潮]暂未支持的角色，请等待后续更新\n")
                return f"角色_{role_id}"

            return result
        except Exception as e:
            logger.exception(f"获取角色模版失败: {role_id}", e)
            return f"角色_{role_id}"

    def _get_phantom_detail(self, phantom_id: int) -> EchoModel | None:
        """獲取聲骸信息"""
        monster_id = (
            phantom_id // 10
        )  # phantom_id = monster_id + rarity (一位数字表示声骸品质)
        echo_detail = get_echo_model(monster_id)
        if echo_detail:
            return echo_detail

        m_id_strange = m_id2monsterId_strange.get(str(monster_id))
        if m_id_strange:
            echo_detail = get_echo_model(m_id_strange)
            if echo_detail:
                return echo_detail

        if phantom_id in self.phantom_index:
            echo_detail = get_echo_model(self.phantom_index[phantom_id])
            if echo_detail:
                logger.warning("遍历json拿到mid")
                return echo_detail

        return

    def _get_property_name(self, property_id: int) -> str:
        """獲取屬性名稱"""
        # 先檢查補充的屬性映射
        if 0 <= property_id < 99:
            if property_id in sub_props:
                prop_info = sub_props[property_id]
                return prop_info["name"]
        elif 1000 < property_id < 9999:
            choice_id = property_id % 1000
            if choice_id in main_first_props:
                prop_info = main_first_props[choice_id]
                return prop_info["name"]
        elif 10000 < property_id < 99999:
            choice_id = property_id % 10000
            if choice_id in main_second_props:
                prop_info = main_second_props[choice_id]
                return prop_info["name"]

        # 再檢查標準屬性索引
        if property_id in self.property_index:
            prop_info = self.property_index[property_id]
            name = prop_info["name"]
            logger.warning("遍历json拿到property_name")
            return name

        return f"缺失名称(ID:{property_id})"

    def _is_property_percent(self, property_id: int) -> bool:
        """檢查屬性是否為百分比類型"""
        # 先檢查補充的屬性映射
        if 0 <= property_id < 99:
            if property_id in sub_props:
                return sub_props[property_id]["isPercent"]
        elif 1000 < property_id < 9999:
            choice_id = property_id % 1000
            if choice_id in main_first_props:
                return main_first_props[choice_id]["isPercent"]
        elif 10000 < property_id < 99999:
            choice_id = property_id % 10000
            if choice_id in main_second_props:
                return main_second_props[choice_id]["isPercent"]

        # 再檢查標準屬性索引
        if property_id in self.property_index:
            logger.warning("遍历json拿到property_isPercent")
            return self.property_index[property_id]["isPercent"]

        return False  # 默認不是百分比

    def _build_chain_list(self, role_info: RoleInfo, role) -> List[Dict[str, Any]]:
        """构建共鸣链列表"""
        if not role_info.resonant_chain_group_index:
            role_info.resonant_chain_group_index = 0

        # resonant_chain_group_index 为解锁的共鸣链数量
        chainList = []
        for chain in role.chainList:
            if chain.order <= role_info.resonant_chain_group_index:
                chain.unlocked = True
            chainList.append(
                {
                    "name": chain.name,
                    "order": chain.order,
                    "description": chain.description,
                    "iconUrl": chain.iconUrl,
                    "unlocked": chain.unlocked,
                }
            )
        return chainList

    def _build_skill_list(self, role_info: RoleInfo, role) -> List[Dict[str, Any]]:
        """构建技能列表"""
        # 如果沒有技能数据，返回空列表
        if not role_info.skills:
            return []

        # 找到最低值的key
        min_value_skill = min(role_info.skills, key=lambda x: x["value"])
        min_key = min_value_skill["key"]

        # 创建一个字典，方便通过key查找value
        skill_dict = {skill["key"]: skill["value"] for skill in role_info.skills}

        # 定义需要获取的位置和对应的key
        # 假设key的格式是1001XXX，其中XXX表示位置
        # 我们需要获取第1,2,3,6,7位置的key
        base_key = min_key // 100  # 获取基础key部分(10012或10008)
        position_keys = [
            base_key * 100 + 1,  # 位置1 普攻
            base_key * 100 + 2,  # 位置2 共技
            base_key * 100 + 3,  # 位置3 回路
            base_key * 100 + 6,  # 位置6 解放
            base_key * 100 + 7,  # 位置7 变奏
        ]

        # 获取对应位置的value值，如果没有则使用默认值1
        position_values = []
        for key in position_keys:
            if key in skill_dict:
                position_values.append(skill_dict[key])
            else:
                position_values.append(1)  # 默认值

        # 技能列表
        skillList = []

        for i, skill_data in enumerate(role.skillList):
            # 只处理前5个元素
            if i < 5:
                get_level = position_values[i] if i < len(position_values) else 1
            else:
                # 第6个元素使用默认值或原始值
                get_level = 1

            skill = skill_data.skill
            skillList.append(
                {
                    "level": get_level,
                    "skill": {
                        "description": skill.description,
                        "iconUrl": skill.iconUrl,
                        "id": skill.id,
                        "name": skill.name,
                        "type": skill.type,
                    },
                }
            )

        return skillList

    def _build_weapon_data(self, role_id: int, role) -> Dict[str, Any]:
        """構建武器數據"""
        # 查找對應的武器數據
        weapon_info = None
        for weapon_id, weapon in self.weapon_data.items():
            # 根据角色 ID 匹配对应的武器
            if hasattr(weapon, "role_id") and weapon.role_id == role_id:
                weapon_info = weapon
                break

        # 处理 `weaponData` 的数据
        weaponData = {
            "breach": role.weaponData.breach,
            "level": role.weaponData.level,
            "resonLevel": role.weaponData.resonLevel,
            "weapon": {
                "weaponEffectName": role.weaponData.weapon.weaponEffectName,
                "weaponIcon": role.weaponData.weapon.weaponIcon,
                "weaponId": role.weaponData.weapon.weaponId,
                "weaponName": role.weaponData.weapon.weaponName,
                "weaponStarLevel": role.weaponData.weapon.weaponStarLevel,
                "weaponType": role.weaponData.weapon.weaponType,
            },
        }
        if weapon_info:
            # breach 突破、resonLevel 精炼
            weaponData["level"] = weapon_info.level
            weaponData["breach"] = get_breach(weapon_info.level)
            weaponData["weapon"]["weaponId"] = weapon_info.weapon_id
            weaponData["resonLevel"] = weapon_info.reson_level
            weapon_detail = get_weapon_detail(weapon_info.weapon_id, weapon_info.level)
            weaponData["weapon"]["weaponName"] = weapon_detail.name
            weaponData["weapon"]["weaponStarLevel"] = weapon_detail.starLevel

        return weaponData

    async def _build_phantom_data(self, role_id: int, role) -> Dict[str, Any]:
        """構建聲骸數據"""
        # 查找對應的聲骸數據
        role_phantoms = self.phantom_data.get(role_id)
        if not role_phantoms or not role_phantoms.phantom_incr_list:
            return {"cost": 0, "equipPhantomList": []}

        logger.debug(f"角色 {role.role.roleName} 构建声骸中")
        equip_phantom_list = []
        total_cost = 0

        for position, phantom_detail in enumerate(role_phantoms.phantom_incr_list, 1):
            phantom_id = phantom_detail.get("id")  # 使用 id 而不是 phantom_id
            fetter_group_id = phantom_detail.get("fetter_group_id")
            phantom_level = phantom_detail.get("phantom_level")
            logger.debug(
                f"position:{position}, phantom_id:{phantom_id}, fetter_group_id:{fetter_group_id}, phantom_level:{phantom_level}"
            )

            # 根據聲骸ID確定cost
            # monster_id = phantom_id // 10   # phantom_id = monster_id + rarity (一位数字表示声骸品质)
            rarity = phantom_id % 10
            # echo_detail = get_echo_model(monster_id)

            echo_detail = self._get_phantom_detail(phantom_id)
            if not echo_detail:
                logger.error(
                    f"[鸣潮] 角色 {role.role.roleName} 无法匹配到的声骸id: {phantom_id}"
                )
                # 在非异步函数里调用异步函数
                await send_master_info(
                    f"[鸣潮] 角色 {role.role.roleName} 无法匹配到的声骸id: {phantom_id}"
                )
                continue

            monster_id = echo_detail.id  # 重定向

            cost = echo_detail.get_cost()
            total_cost += cost

            # 獲取聲骸名稱
            phantom_name = echo_detail.name

            # 獲取套裝名稱
            fetter_group_name = echo_detail.get_group_name_by_gid(fetter_group_id)
            logger.debug(f"角色 {role.role.roleName} 添加声骸: {phantom_name} (套装：{fetter_group_name} ID: {phantom_id})")

            # 構建聲骸數據結構，符合 EquipPhantom 模型
            phantom_data = {
                "cost": cost,
                "level": phantom_level,
                "quality": rarity,  # 默認品質
                "fetterDetail": {
                    "firstDescription": "",
                    "groupId": fetter_group_id,
                    "iconUrl": "",
                    "name": fetter_group_name,
                    "num": len(role_phantoms.phantom_incr_list),
                    "secondDescription": "",
                    "tripleDescription": "",
                },
                "mainProps": self._convert_phantom_props(
                    phantom_detail.get("phantom_main_prop", [])
                ),
                "phantomProp": {
                    "cost": cost,
                    "iconUrl": "",
                    "name": phantom_name,
                    "phantomId": monster_id,  # monster_id
                    "phantomPropId": phantom_id,  # 保持
                    "quality": rarity,  # 默認品質
                    "skillDescription": "",
                },
                "subProps": self._convert_phantom_props(
                    phantom_detail.get("phantom_sub_prop", [])
                ),
            }
            equip_phantom_list.append(phantom_data)

        return {
            "cost": total_cost,
            "equipPhantomList": (equip_phantom_list if equip_phantom_list else []),
        }

    def _convert_phantom_props(self, props: List[Dict]) -> List[Dict]:
        """轉換聲骸屬性格式"""
        converted_props = []
        for prop in props:
            prop_id = prop.get("phantom_prop_id", 0)
            value = prop.get("value", 0)

            # 使用新的屬性映射獲取屬性名稱
            display_name = self._get_property_name(prop_id)

            # 格式化屬性值
            formatted_value = self._format_property_value(prop_id, value)

            converted_props.append(
                {
                    "attributeName": display_name,
                    "attributeValue": formatted_value,
                }
            )
        logger.debug(f"转换属性: {converted_props}, props原始数据: {props}")
        return converted_props

    def _format_property_value(self, prop_id: int, value) -> str:
        """格式化屬性值"""
        # 如果value已經是字符串且包含%，直接返回
        if isinstance(value, str) and "%" in value:
            return value

        # 嘗試將value轉換為數字
        try:
            if isinstance(value, str):
                # 移除可能的百分比符號
                numeric_value = float(value.replace("%", ""))
            else:
                numeric_value = float(value)
        except (ValueError, TypeError):
            # 如果轉換失敗，返回原始值
            return str(value)

        # 檢查是否為百分比屬性
        if self._is_property_percent(prop_id):
            # 修復：將原始數值轉換為正確的百分比格式
            # 原始機器人期望的格式是 22.0% 而不是 2200.0%
            if numeric_value > 100:
                # 如果數值大於100，說明是原始數值（以100為基數），需要除以100
                percentage_value = numeric_value / 100.0
                return f"{percentage_value:.2f}%"
            else:
                # 如果數值小於等於100，直接使用
                return f"{numeric_value:.2f}%"
        else:
            # 數值屬性，直接顯示整數
            return str(int(numeric_value))
