"""队友合鸣注册：条件写在类中，数值复用现有合鸣 JSON 缓存。"""

from ..api.model import RoleDetailData
from ..ascension.constant import sum_numbers, sum_percentages
from ..ascension.sonata import get_sonata_detail
from .abstract import SonataAbstract, WavesSonataRegister
from .damage import DamageAttribute, check_char_id
from .utils import (
    CHAR_ATTR_CELESTIAL,
    CHAR_ATTR_FREEZING,
    CHAR_ATTR_MOLTEN,
    CHAR_ATTR_SIERRA,
    CHAR_ATTR_SINKING,
    CHAR_ATTR_VOID,
    Ancient_Role_Ids,
    Havoc_Bane_Role_Ids,
    Spectro_Frazzle_Role_Ids,
    Sync_Strike_Role_Ids,
    attack_damage,
    cast_attack,
    cast_healing,
    cast_hit,
    cast_liberation,
    cast_skill,
    hit_damage,
    liberation_damage,
    phantom_damage,
    skill_damage,
    temp_atk,
)


def _param(name: str, index: int) -> float:
    detail = get_sonata_detail(name)
    piece = detail.piece(detail.full_piece_effect())
    value = piece.param[index]
    return float(value.removesuffix("%")) / (100 if value.endswith("%") else 1)


class Sonata_凝夜白霜(SonataAbstract):
    name = "凝夜白霜"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if attr.char_attr != CHAR_ATTR_FREEZING:
            return
        if cast_hit in damage_func or cast_attack in damage_func:
            # 声骸五件套
            title = f"合鸣效果-{self.name}"
            msg = "使用普攻或重击时，冷凝伤害提升10%，该效果可叠加三层，持续15秒"
            attr.add_dmg_bonus(0.3, title, msg)


class Sonata_熔山裂谷(SonataAbstract):
    name = "熔山裂谷"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if attr.char_attr != CHAR_ATTR_MOLTEN:
            return
        if cast_skill in damage_func:
            title = f"合鸣效果-{self.name}"
            msg = "使用共鸣技能时，热熔伤害提升30%，持续15秒"
            attr.add_dmg_bonus(0.3, title, msg)


class Sonata_彻空冥雷(SonataAbstract):
    name = "彻空冥雷"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if cast_skill in damage_func and attr.char_attr == CHAR_ATTR_VOID:
            title = f"合鸣效果-{self.name}"
            msg = "使用共鸣技能时，获得一层导电伤害提升15%"
            attr.add_dmg_bonus(0.15, title, msg)
        if cast_hit in damage_func and attr.char_attr == CHAR_ATTR_VOID:
            title = f"合鸣效果-{self.name}"
            msg = "使用重击时，获得一层导电伤害提升15%"
            attr.add_dmg_bonus(0.15, title, msg)


class Sonata_啸谷长风(SonataAbstract):
    name = "啸谷长风"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if not isGroup:
            return
        if attr.char_attr != CHAR_ATTR_SIERRA:
            return
        # 声骸五件套
        title = f"合鸣效果-{self.name}"
        msg = "使用变奏技能登场时，气动伤害提升30%，持续15秒"
        attr.add_dmg_bonus(0.3, title, msg)


class Sonata_浮星祛暗(SonataAbstract):
    name = "浮星祛暗"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if not isGroup:
            return
        if attr.char_attr != CHAR_ATTR_CELESTIAL:
            return
        title = f"合鸣效果-{self.name}"
        msg = "使用变奏技能登场时，衍射伤害提升30%，持续15秒"
        attr.add_dmg_bonus(0.3, title, msg)


class Sonata_沉日劫明(SonataAbstract):
    name = "沉日劫明"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if attr.char_attr != CHAR_ATTR_SINKING:
            return
        if cast_hit in damage_func or cast_attack in damage_func:
            title = f"合鸣效果-{self.name}"
            msg = "使用普攻或重击时，湮灭伤害提升7.5%，该效果可叠加四层，持续15秒"
            attr.add_dmg_bonus(0.3, title, msg)


class Sonata_隐世回光(SonataAbstract):
    name = "隐世回光"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_template == temp_atk:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if not isHealing:
            return
        if attr.char_template != "temp_atk":
            return
        title = f"合鸣效果-{self.name}"
        self.effect(attr, title)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_atk_percent(_param(self.name, 0), title, "治疗后全队攻击提升15%")


class Sonata_轻云出月(SonataAbstract):
    name = "轻云出月"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_template == temp_atk:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        pass

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_atk_percent(_param(self.name, 0), title, "延奏后下一位角色攻击提升22.5%")


class Sonata_不绝余音(SonataAbstract):
    name = "不绝余音"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if attr.char_template != "temp_atk":
            return
        title = f"合鸣效果-{self.name}"
        msg = "在场时，自身攻击每1.5秒提升5%，该效果最多叠加四层"
        attr.add_atk_percent(0.2, title, msg)


class Sonata_凌冽决断之心(SonataAbstract):
    name = "凌冽决断之心"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if cast_skill in damage_func and attr.char_attr == CHAR_ATTR_FREEZING:
            title = f"合鸣效果-{self.name}"
            msg = "施放共鸣技能时，自身冷凝伤害提升22.5%"
            attr.add_dmg_bonus(0.225, title, msg)
        if cast_liberation in damage_func and attr.char_damage == skill_damage:
            title = f"合鸣效果-{self.name}"
            if check_char_id(attr, [1107]):
                msg = "施放共鸣解放时，自身共鸣技能伤害提升18%*2"
                attr.add_dmg_bonus(0.18 * 2, title, msg)
            else:
                title = f"合鸣效果-{self.name}"
                msg = "施放共鸣解放时，自身共鸣技能伤害提升18%"
                attr.add_dmg_bonus(0.18, title, msg)


class Sonata_高天共奏之曲(SonataAbstract):
    name = "高天共奏之曲"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_template == temp_atk and not set(attr.teammate_char_ids or ()).isdisjoint(Sync_Strike_Role_Ids):
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if attr.sync_strike:
            title = f"合鸣效果-{self.name}"
            msg = "当前角色协同攻击造成的伤害提升80%"
            attr.add_dmg_bonus(0.8, title, msg)

            # 协同攻击命中敌人且暴击时，队伍中登场角色攻击力提升20%
            if attr.char_template == "temp_atk":
                title = f"合鸣效果-{self.name}"
                self.effect(attr, title)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_atk_percent(_param(self.name, 1), title, "协同攻击暴击后队伍攻击提升20%")


class Sonata_幽夜隐匿之帷(SonataAbstract):
    name = "幽夜隐匿之帷"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_attr == CHAR_ATTR_SINKING:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色触发延奏技能离场时，额外对周围敌人造成480%的湮灭伤害，该伤害为延奏技能伤害，并使下一个登场角色湮灭属性伤害加成提升15%，持续15秒
        pass

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_dmg_bonus(_param(self.name, 1), title, "延奏后下一位湮灭伤害提升15%")


class Sonata_此间永驻之光(SonataAbstract):
    name = "此间永驻之光"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if not check_char_id(attr, Spectro_Frazzle_Role_Ids):
            return
        # 角色为敌人添加【光噪效应】时，自身暴击提升20%，持续15秒；攻击存在10层【光噪效应】的敌人时，自身衍射伤害加成提升15%，持续15秒。
        title = f"合鸣效果-{self.name}"
        msg = "角色为敌人添加【光噪效应】时，自身暴击提升20%"
        attr.add_crit_rate(0.2, title, msg)
        if attr.char_attr == CHAR_ATTR_CELESTIAL:
            msg = "攻击存在10层【光噪效应】的敌人时，自身衍射伤害加成提升15%"
            attr.add_dmg_bonus(0.15, title, msg)


class Sonata_无惧浪涛之勇(SonataAbstract):
    name = "无惧浪涛之勇"

    def do_panel(self, card_sort_map: dict, result: dict, role_id: int):
        applied = card_sort_map.setdefault("sonata_applied", {}).setdefault(self.name, [])
        if "atk_percent" not in applied:
            value = _param(self.name, 0)
            result["atk_percent"] = result.get("atk_percent", 0) + value
            base_atk = float(card_sort_map["char_atk"]) + float(card_sort_map["weapon_atk"])
            # 数值面板与计算百分比都补入，但这不是固定攻击，不写atk_flat。
            result["攻击"] = sum_numbers(result.get("攻击", 0), base_atk * value)
            applied.append("atk_percent")
        if card_sort_map["energy_regen"] >= _param(self.name, 1) and "dmg_bonus" not in applied:
            card_sort_map["属性伤害加成"] = sum_percentages(
                card_sort_map.get("属性伤害加成", "0%"), f"{_param(self.name, 2) * 100:g}%"
            )
            applied.append("dmg_bonus")
        card_sort_map["ph_result"] = True

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        title = f"合鸣效果-{self.name}"
        applied = attr.sonata_applied.setdefault(self.name, [])
        if attr.char_template == temp_atk:
            value = _param(self.name, 0)
            msg = f"角色攻击提升{value * 100:g}%"
            if "atk_percent" in applied:
                attr.add_effect(title, msg)
            else:
                attr.add_atk_percent(value, title, msg)
                applied.append("atk_percent")
        if "dmg_bonus" in applied:
            attr.add_effect(title, f"全属性伤害提升{_param(self.name, 2) * 100:g}%")
        else:
            self.effect(attr)

    def effect(self, attr: DamageAttribute):
        # 面板/phase之后的声骸与武器仍可能提升共效，按结算时实际值补齐一次。
        applied = attr.sonata_applied.setdefault(self.name, [])
        if "dmg_bonus" in applied or attr.energy_regen < _param(self.name, 1):
            return
        value = _param(self.name, 2)
        title = f"合鸣效果-{self.name}"
        msg = f"共鸣效率达到{_param(self.name, 1) * 100:g}%,全属性伤害提升{value * 100:g}%"
        attr.add_dmg_bonus(value, title, msg)
        applied.append("dmg_bonus")

    def do_finalize(self, attr: DamageAttribute):
        self.effect(attr)


class Sonata_流云逝尽之空(SonataAbstract):
    name = "流云逝尽之空"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_attr == CHAR_ATTR_SIERRA and attr.env_aero_erosion:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【风蚀效应】时，队伍中角色气动伤害提升15%，自身气动伤害额外提升15%，持续20秒。
        if attr.char_attr != CHAR_ATTR_SIERRA:
            return
        if attr.env_aero_erosion:
            title = f"合鸣效果-{self.name}"
            self.effect(attr, title)

            title = f"合鸣效果-{self.name}"
            msg = "自身气动伤害额外提升15%"
            attr.add_dmg_bonus(0.15, title, msg)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_dmg_bonus(_param(self.name, 0), title, "添加风蚀后队伍气动伤害提升15%")


class Sonata_愿戴荣光之旅(SonataAbstract):
    name = "愿戴荣光之旅"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 攻击命中存在【风蚀效应】的敌人时，自身暴击提升10%，气动伤害提升30%，持续10秒。
        if attr.env_aero_erosion:
            title = f"合鸣效果-{self.name}"
            msg = "攻击命中存在【风蚀效应】的敌人时，自身暴击提升10%"
            attr.add_crit_rate(0.1, title, msg)
            if attr.char_attr == CHAR_ATTR_SIERRA:
                msg = "气动伤害提升30%"
                attr.add_dmg_bonus(0.3, title, msg)


class Sonata_奔狼燎原之焰(SonataAbstract):
    name = "奔狼燎原之焰"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_attr == CHAR_ATTR_MOLTEN:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 施放共鸣解放时，队伍中角色热熔伤害提升15%，自身共鸣解放伤害提升20%，持续35秒。
        if attr.char_attr == CHAR_ATTR_MOLTEN:
            title = f"合鸣效果-{self.name}"
            self.effect(attr, title)

        if attr.char_damage == liberation_damage:
            title = f"合鸣效果-{self.name}"
            msg = "自身共鸣解放伤害提升20%"
            attr.add_dmg_bonus(0.2, title, msg)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_dmg_bonus(_param(self.name, 0), title, "施放共鸣解放后队伍热熔伤害提升15%")


class Sonata_失序彼岸之梦(SonataAbstract):
    name = "失序彼岸之梦"
    pieces = 3

    def do_panel(self, card_sort_map: dict, result: dict, role_id: int):
        # 沿用现有零共鸣能量角色假设；20%暴击和35%声骸伤害均来自JSON。
        if role_id not in Ancient_Role_Ids:
            return
        card_sort_map["暴击"] = sum_percentages(card_sort_map.get("暴击", "0%"), f"{_param(self.name, 1) * 100:g}%")
        card_sort_map["声骸技能伤害加成"] = sum_percentages(
            card_sort_map.get("声骸技能伤害加成", "0%"), f"{_param(self.name, 2) * 100:g}%"
        )
        card_sort_map.setdefault("sonata_applied", {})[self.name] = ["crit_rate", "phantom_damage"]
        card_sort_map["ph_result"] = True

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        title = f"合鸣效果-{self.name}"
        applied = attr.sonata_applied.setdefault(self.name, [])
        if attr.char_template == temp_atk:
            value = _param(self.name, 1)
            msg = f"角色共鸣能量为0时,自身暴击率提升{value * 100:g}%"
            if "crit_rate" in applied:
                attr.add_effect(title, msg)
            else:
                attr.add_crit_rate(value, title, msg)
                applied.append("crit_rate")
        if attr.char_damage == phantom_damage:
            value = _param(self.name, 2)
            msg = f"角色共鸣能量为0时,声骸技能伤害加成提升{value * 100:g}%"
            if "phantom_damage" in applied:
                attr.add_effect(title, msg)
            else:
                attr.add_dmg_bonus(value, title, msg)
                applied.append("phantom_damage")


class Sonata_荣斗铸锋之冠(SonataAbstract):
    name = "荣斗铸锋之冠"
    pieces = 3

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色获得护盾时，自身攻击提升6%，暴击伤害提升4%，该效果可叠加5层，持续4秒，每0.5秒可触发一次。
        if not attr.trigger_shield:
            return
        title = f"合鸣效果-{self.name}"
        msg = "角色获得护盾时，自身攻击提升6%*5"
        attr.add_atk_percent(0.06 * 5, title, msg)
        msg = "角色获得护盾时，自身暴击伤害提升4%*5"
        attr.add_crit_dmg(0.04 * 5, title, msg)


class Sonata_息界同调之律(SonataAbstract):
    pieces = 3
    name = "息界同调之律"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_damage == phantom_damage:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色施放声骸技能时，自身重击伤害加成提升30%，持续4秒；队伍中角色声骸技能伤害加成提升4%，该效果可叠加4层，持续30秒。
        if attr.char_damage == hit_damage:
            title = f"合鸣效果-{self.name}"
            msg = "角色施放声骸技能时，自身重击伤害加成提升30%"
            attr.add_dmg_bonus(0.3, title, msg)
        if attr.char_damage == phantom_damage:
            title = f"合鸣效果-{self.name}"
            self.effect(attr, title)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_dmg_bonus(_param(self.name, 2) * _param(self.name, 3), title, "队伍声骸技能伤害提升4%*4")


class Sonata_焚羽猎魔之影(SonataAbstract):
    name = "焚羽猎魔之影"
    pieces = 3

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色造成声骸技能伤害时，重击伤害的暴击提升20%，持续6秒；造成重击伤害时，声骸技能伤害的暴击提升20%，持续6秒。同时拥有两种效果时，自身热熔伤害提升16%。
        if attr.char_damage == hit_damage:
            title = f"合鸣效果-{self.name}"
            msg = "造成声骸技能伤害后,重击暴击提升20%"
            attr.add_crit_rate(_param(self.name, 0), title, msg)
        if attr.char_damage == phantom_damage:
            title = f"合鸣效果-{self.name}"
            msg = "造成重击伤害后,声骸技能暴击提升20%"
            attr.add_crit_rate(_param(self.name, 2), title, msg)

        if attr.role and attr.role.role.roleId == 1208:
            title = f"合鸣效果-{self.name}"
            msg = "自身热熔伤害提升16%"
            attr.add_dmg_bonus(0.16, title, msg)


class Sonata_命理崩毁之弦(SonataAbstract):
    name = "命理崩毁之弦"
    pieces = 3

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if not check_char_id(attr, Havoc_Bane_Role_Ids):
            return
        # 角色为敌人添加【虚湮效应】时，自身攻击提升20%，共鸣解放伤害加成提升30%，持续5秒。
        title = f"合鸣效果-{self.name}"
        msg = "角色为敌人添加【虚湮效应】时，自身攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)
        if attr.char_damage == liberation_damage:
            msg = "角色为敌人添加【虚湮效应】时，共鸣解放伤害加成提升30%"
            attr.add_dmg_bonus(0.3, title, msg)


class Sonata_逆光跃彩之约(SonataAbstract):
    name = "逆光跃彩之约"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_template == temp_atk:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色施放延奏技能后，下一个变奏技能登场的角色攻击提升15%，其每点谐度破坏增幅还会使攻击额外提升0.3%，上限15%，持续15秒，若切换至其他角色则该效果提前结束。
        pass

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_atk_percent(_param(self.name, 0), title, "延奏后下一位角色攻击提升15%")
        # 读受益者在合鸣应用阶段的增幅；后续装备增幅不追溯重算。
        value = min(max(0, attr.tune_break_boost) * _param(self.name, 1), _param(self.name, 2))
        if value:
            attr.add_atk_percent(value, title, f"谐度破坏增幅转攻击,当前{value * 100:.1f}%")


class Sonata_流金溯真之式(SonataAbstract):
    name = "流金溯真之式"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色造成普攻伤害时，自身衍射伤害提升10%，该效果可叠加3层，持续5秒。
        # 叠至3层时，施放共鸣解放时，普攻伤害加成提升40%。
        if cast_attack not in damage_func:
            return
        title = f"合鸣效果-{self.name}"
        if attr.char_attr == CHAR_ATTR_CELESTIAL:
            msg = "角色造成普攻伤害时，自身衍射伤害提升10%，可叠加3层"
            attr.add_dmg_bonus(0.3, title, msg)
        if cast_liberation in damage_func and attr.char_damage == attack_damage:
            msg = "叠至3层时，施放共鸣解放时，普攻伤害加成提升40%"
            attr.add_dmg_bonus(0.4, title, msg)


class Sonata_星构寻辉之环(SonataAbstract):
    name = "星构寻辉之环"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_template == temp_atk:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 为队伍中角色提供治疗时，自身每1%的偏谐值累积效率使队伍中角色攻击提升0.2%，上限25%
        if attr.char_template != "temp_atk":
            return
        title = f"合鸣效果-{self.name}"
        self.effect(attr, title, holder_rate=attr.off_tune_buildup_rate)

    def effect(self, attr: DamageAttribute, title: str, holder_rate: float | None = None):
        # 队友持有者面板不可得，沿用满额假设；自身保留偏谐累积效率实际值。
        value = (
            _param(self.name, 2)
            if holder_rate is None
            else min(holder_rate * _param(self.name, 1) / _param(self.name, 0), _param(self.name, 2))
        )
        attr.add_atk_percent(value, title, f"治疗后队伍攻击提升,当前{value * 100:.2f}%")


class Sonata_长路启航之星(SonataAbstract):
    name = "长路启航之星"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【聚爆效应】或【震谐·偏移】时，自身暴击提升20%，热熔伤害提升20%
        if not attr.env_tune_rupture and not attr.env_fusion_burst:
            return
        title = f"合鸣效果-{self.name}"
        msg = "角色为敌人添加【聚爆效应】或【震谐·偏移】时，自身暴击提升20%"
        attr.add_crit_rate(0.2, title, msg)
        if attr.char_attr == CHAR_ATTR_MOLTEN:
            msg = "角色为敌人添加【聚爆效应】或【震谐·偏移】时，自身热熔伤害提升20%"
            attr.add_dmg_bonus(0.2, title, msg)


class Sonata_斑驳粉饰之沫(SonataAbstract):
    name = "斑驳粉饰之沫"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.env_fusion_burst and attr.char_attr == CHAR_ATTR_MOLTEN:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【聚爆效应】时，自身获得下述效果：热熔伤害提升10%
        # 持续期间内施放延奏技能后，下一个变奏技能登场的角色热熔伤害提升25%
        if attr.char_attr != CHAR_ATTR_MOLTEN or not attr.env_fusion_burst:
            return
        title = f"合鸣效果-{self.name}"
        msg = "角色为敌人添加【聚爆效应】时，自身热熔伤害提升10%"
        attr.add_dmg_bonus(0.1, title, msg)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_dmg_bonus(_param(self.name, 2), title, "聚爆延奏后下一位热熔伤害提升25%")


class Sonata_听唤语义之愿(SonataAbstract):
    name = "听唤语义之愿"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色造成声骸技能伤害时，声骸技能伤害的暴击提升20%，自身气动伤害提升15%
        if attr.char_damage != phantom_damage:
            return
        title = f"合鸣效果-{self.name}"
        msg = "角色造成声骸技能伤害时，声骸技能伤害的暴击提升20%"
        attr.add_crit_rate(0.2, title, msg)
        if attr.char_attr == CHAR_ATTR_SIERRA:
            msg = "角色造成声骸技能伤害时，自身气动伤害提升15%"
            attr.add_dmg_bonus(0.15, title, msg)


class Sonata_雪落无声之愿(SonataAbstract):
    name = "雪落无声之愿"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.env_glacio_chafe and attr.char_attr == CHAR_ATTR_FREEZING:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【霜渐效应】时，冷凝伤害提升10%，持续15秒。自身获得【落雪】效果
        # 拥有【落雪】效果时：
        # \n·角色造成共鸣解放伤害时，将清除【落雪】效果，使自身暴击提升25%，持续6秒。
        # \n·角色施放延奏技能时，将清除【落雪】效果，使下一个变奏技能登场的角色冷凝伤害提升25%
        if not attr.env_glacio_chafe:
            return
        title = f"合鸣效果-{self.name}"
        if attr.char_attr == CHAR_ATTR_FREEZING:
            msg = "添加【霜渐效应】时，冷凝伤害提升10%,自身获得【落雪】效果"
            attr.add_dmg_bonus(0.1, title, msg)
        if attr.char_damage == liberation_damage:
            msg = "拥有【落雪】效果时,造成共鸣解放伤害时，使自身暴击提升25%"
            attr.add_crit_rate(0.25, title, msg)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_dmg_bonus(_param(self.name, 6), title, "落雪延奏后下一位冷凝伤害提升25%")


class Sonata_剪心辑梦之影(SonataAbstract):
    name = "剪心辑梦之影"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.is_env_shifting():
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【震谐·偏移】或【集谐·偏移】时，队伍中角色谐度破坏增幅提升20点
        if not attr.is_env_shifting():
            return
        title = f"合鸣效果-{self.name}"
        self.effect(attr, title)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_tune_break_boost(_param(self.name, 0), title, "添加偏移后队伍谐度破坏增幅提升20点")


class Sonata_碎梦亡鬼之魇(SonataAbstract):
    name = "碎梦亡鬼之魇"
    pieces = 1

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【骇破·偏移】时，自身普攻伤害加成和重击伤害加成提升35%，持续15秒
        if not attr.env_hack:
            return
        title = f"合鸣效果-{self.name}"
        if attr.char_damage == hit_damage:
            msg = "添加【骇破·偏移】，自身重击伤害加成提升35%"
            attr.add_dmg_bonus(0.35, title, msg)
        if attr.char_damage == attack_damage:
            msg = "添加【骇破·偏移】，自身普攻伤害加成提升35%"
            attr.add_dmg_bonus(0.35, title, msg)


class Sonata_冥途夜行之灯(SonataAbstract):
    name = "冥途夜行之灯"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色获得护盾时，自身暴击提升5%，该效果可叠加4层，持续5秒，每0.5秒可触发一次。叠至满层时，自身造成的热熔伤害提升15%。
        if not attr.trigger_shield:
            return
        title = f"合鸣效果-{self.name}"
        msg = "添加4层【护盾】，自身暴击提升5%*4"
        attr.add_crit_rate(0.2, title, msg)
        if attr.char_attr == CHAR_ATTR_MOLTEN:
            msg = "添加4层【护盾】，自身造成的热熔伤害提升15%"
            attr.add_dmg_bonus(0.15, title, msg)


class Sonata_清邪荡煞之心(SonataAbstract):
    name = "清邪荡煞之心"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【集谐·偏移】时，自身暴击伤害提升20%，气动伤害提升30%，持续15秒。
        if not attr.env_tune_strain:
            return
        title = f"合鸣效果-{self.name}"
        msg = "添加【集谐·偏移】，自身暴击伤害提升20%"
        attr.add_crit_dmg(0.2, title, msg)
        if attr.char_attr == CHAR_ATTR_SIERRA:
            msg = "添加【集谐·偏移】，气动伤害提升30%"
            attr.add_dmg_bonus(0.3, title, msg)


class Sonata_羽落空尘之歌(SonataAbstract):
    name = "羽落空尘之歌"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_template == temp_atk and attr.env_glacio_chafe:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【虚湮效应】时，获得【玄翎之羽】：自身暴击提升20%，重击伤害加成提升35%，持续15秒。
        if attr.env_havoc_bane:
            title = f"合鸣效果-{self.name}"
            msg = "玄翎之羽：自身暴击提升20%"
            attr.add_crit_rate(0.2, title, msg)
            if attr.char_damage == hit_damage:
                msg = "玄翎之羽：重击伤害加成提升35%"
                attr.add_dmg_bonus(0.35, title, msg)
            return
        # 角色为敌人添加【霜渐效应】时，获得【重明之羽】：自身每1%的共鸣效率使队伍中角色攻击提升0.1%，上限25%，持续10秒。
        if attr.env_glacio_chafe:
            title = f"合鸣效果-{self.name}"
            self.effect(attr, title, holder_rate=attr.energy_regen)
            return

    def effect(self, attr: DamageAttribute, title: str, holder_rate: float | None = None):
        # 队友默认持有者共鸣效率达到250%，取上限；自身显式传入自己的效率。
        value = (
            _param(self.name, 5)
            if holder_rate is None
            else min(_param(self.name, 4) * (holder_rate * 100 // 1), _param(self.name, 5))
        )
        attr.add_atk_percent(value, title, f"重明之羽：队伍攻击提升,当前{value * 100:.1f}%")


class Sonata_衔梦照世之心(SonataAbstract):
    name = "衔梦照世之心"

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if not (attr.env_electro_flare or attr.env_unison or attr.env_unison_response):
            return
        title = f"合鸣效果-{self.name}"
        attr.add_crit_rate(0.15, title, "附加电磁效应或获得/响应同奏后30秒内，暴击提升15%")
        if attr.char_attr == CHAR_ATTR_VOID:
            attr.add_dmg_bonus(0.225, title, "附加电磁效应或获得/响应同奏后30秒内，导电伤害提升22.5%")


class Sonata_镜影流电之瞬(SonataAbstract):
    name = "镜影流电之瞬"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.env_electro_flare and attr.char_attr == CHAR_ATTR_VOID:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        # 角色为敌人添加【电磁效应】时，自身导电伤害提升10%，持续15秒。
        if attr.env_electro_flare and attr.char_attr == CHAR_ATTR_VOID:
            title = f"合鸣效果-{self.name}"
            msg = "添加【电磁效应】后自身导电伤害提升10%"
            attr.add_dmg_bonus(0.1, title, msg)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_dmg_bonus(_param(self.name, 2), title, "电磁延奏后下一位导电伤害提升25%")


class Sonata_茜染怀想之花(SonataAbstract):
    name = "茜染怀想之花"

    def do_teammate(self, attr: DamageAttribute, char_name: str = "", isGroup: bool = True):
        title = f"{char_name}-合鸣效果-{self.name}" if char_name else f"合鸣效果-{self.name}"
        if attr.char_template == temp_atk:
            self.effect(attr, title)

    def do_phase(
        self,
        attr: DamageAttribute,
        role: RoleDetailData,
        damage_func: list[str] | str,
        isGroup: bool = False,
        isHealing: bool = False,
    ):
        if cast_healing in (damage_func if isinstance(damage_func, list) else [damage_func]):
            title = f"合鸣效果-{self.name}"
            self.effect(attr, title)

    def effect(self, attr: DamageAttribute, title: str):
        attr.add_atk_percent(_param(self.name, 0), title, "治疗后队伍攻击提升10%")
        if attr.env_unison or attr.env_unison_response:
            attr.add_atk_percent(_param(self.name, 2), title, "获得/响应同奏后攻击额外提升15%")


def finalize_sonata(attr: DamageAttribute):
    for ph_detail in attr.ph_detail or ():
        sonata = get_sonata(ph_detail.ph_name, ph_detail.ph_num)
        if sonata:
            sonata.do_finalize(attr)


def get_sonata(name: str, pieces: int) -> SonataAbstract | None:
    if not WavesSonataRegister._id_cls_map:
        register_sonata()
    sonata_clz = WavesSonataRegister.find_class(name)
    return sonata_clz() if sonata_clz and pieces == sonata_clz.pieces else None


def register_sonata():
    for obj in list(globals().values()):
        if isinstance(obj, type) and issubclass(obj, SonataAbstract) and obj is not SonataAbstract and obj.name:
            WavesSonataRegister.register_class(obj.name, obj)
