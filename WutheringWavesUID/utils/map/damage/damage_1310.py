# 漂泊者·导电

import copy
from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    cast_damage,
    cast_liberation,
    cast_skill,
    cast_variation,
    liberation_damage,
    skill_damage,
    skill_damage_calc,
)
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    FC: Literal[
        "Overshock", "ThrumSpectro", "ThrumHavoc", "ThrumAeroSword", "ThrumHavocMid-air", "ThrumAeroMid-air"
    ] = "Overshock",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    if FC == "Overshock":
        title = "超负荷"
        attr.set_char_attr("导电")
        skillParamId = "1"
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    elif FC == "ThrumSpectro":
        title = "千声翻涌·衍射"
        attr.set_char_attr("衍射")
        skillParamId = ["2", "3", "4"]
        for i, skill in enumerate(skillParamId):
            skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skill, skillLevel)
            msg = f"技能倍率{skill_multi}"
            attr.add_skill_multi(skill_multi, title + f"第{i}段", msg)
    elif FC == "ThrumHavoc":
        title = "千声翻涌·湮灭"
        attr.set_char_attr("湮灭")
        skillParamId = ["5", "6", "7"]
        for i, skill in enumerate(skillParamId):
            skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skill, skillLevel)
            msg = f"技能倍率{skill_multi}"
            attr.add_skill_multi(skill_multi, title + f"第{i}段", msg)
    elif FC == "ThrumAeroSword":
        title = "千声翻涌·剑止万律"
        attr.set_char_attr("气动")
        skillParamId = "8"
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    elif FC == "ThrumHavocMid-air":
        title = "千声翻涌·湮灭空中"
        attr.set_char_attr("湮灭")
        skillParamId = ["10", "11", "12"]
        for i, skill in enumerate(skillParamId):
            skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skill, skillLevel)
            msg = f"技能倍率{skill_multi}"
            attr.add_skill_multi(skill_multi, title + f"第{i}段", msg)
    elif FC == "ThrumAeroMid-air":
        title = "千声翻涌·气动空中"
        attr.set_char_attr("气动")
        skillParamId = ["13", "14"]
        for i, skill in enumerate(skillParamId):
            skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skill, skillLevel)
            msg = f"技能倍率{skill_multi}"
            attr.add_skill_multi(skill_multi, title + f"第{i}段", msg)

        title = "千声翻涌·气动下落攻击"
        skillParamId = "16"
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-解明"
        msg = "共鸣技能超负荷对目标造成伤害后附加电磁效应"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

    if role_breach and role_breach >= 4:
        if FC != "Overshock":
            title = "固有技能-归枢！"
            msg = "长按施放超负荷后，自身共鸣技能伤害加成提升20%"
            attr.add_dmg_bonus(0.2, title, msg)

    # 共鸣回路
    title = "共鸣回路-超负荷"
    msg = "短按施放超负荷，队伍中的角色获得10%攻击加成"
    attr.add_atk_percent(0.1, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 3:
        if FC == "Overshock":
            title = f"{role_name}-三链"
            msg = "共鸣技能超负荷伤害倍率提升20%"
            attr.add_skill_ratio(0.6, title, msg)

    if chain_num >= 5:
        if FC != "Overshock":
            title = f"{role_name}-五链"
            msg = "临界共鸣状态期间暴击伤害提升20%"
            attr.add_crit_dmg(0.2, title, msg)

    if chain_num >= 6:
        if FC != "Overshock":
            title = f"{role_name}-六链"
            msg = "共鸣技能千声翻涌和雷陨伤害倍率提升20%"
            attr.add_skill_ratio(0.2, title, msg)

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill, cast_damage, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_2(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    title = "最终战略"
    attr.set_char_attr("导电")
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "1", skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 默认手法
    title = "默认手法"
    msg = "点按超负荷-打满电涌-长按超负荷-大招-千声翻涌"
    attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-解明"
        msg = "共鸣技能超负荷对目标造成伤害后附加电磁效应"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

    # 共鸣回路
    title = "共鸣回路-超负荷"
    msg = "短按施放超负荷，队伍中的角色获得10%攻击加成"
    attr.add_atk_percent(0.1, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "共鸣解放最终战略伤害倍率提升20%"
        attr.add_skill_ratio(0.2, title, msg)

    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "临界共鸣状态期间暴击伤害提升20%"
        attr.add_crit_dmg(0.2, title, msg)

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill, cast_damage, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_3(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
) -> tuple[str, str]:
    title = "地面点按E-千声翻涌总伤"
    msg = "3段·衍射 + 3段·湮灭 + ·剑止万律"
    attr.add_effect(title, msg)

    crit_damage_total, expected_damage_total = 0, 0

    attr_copy = copy.deepcopy(attr)
    crit_damage, expected_damage = calc_damage_1(attr_copy, role, isGroup, FC="ThrumSpectro")
    attr.add_effect("千声翻涌·衍射3段", f"期望伤害:{crit_damage}; 暴击伤害:{expected_damage}")
    crit_damage_total += float(crit_damage.replace(",", ""))
    expected_damage_total += float(expected_damage.replace(",", ""))

    attr_copy = copy.deepcopy(attr)
    crit_damage, expected_damage = calc_damage_1(attr_copy, role, isGroup, FC="ThrumHavoc")
    attr.add_effect("千声翻涌·湮灭3段", f"期望伤害:{crit_damage}; 暴击伤害:{expected_damage}")
    crit_damage_total += float(crit_damage.replace(",", ""))
    expected_damage_total += float(expected_damage.replace(",", ""))

    attr_copy = copy.deepcopy(attr)
    crit_damage, expected_damage = calc_damage_1(attr_copy, role, isGroup, FC="ThrumAeroSword")
    attr.add_effect("千声翻涌·剑止万律", f"期望伤害:{crit_damage}; 暴击伤害:{expected_damage}")
    crit_damage_total += float(crit_damage.replace(",", ""))
    expected_damage_total += float(expected_damage.replace(",", ""))

    return f"{crit_damage_total:,.0f}", f"{expected_damage_total:,.0f}"


def calc_damage_4(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
) -> tuple[str, str]:
    title = "空中点按E-千声翻涌总伤"
    msg = "3段·湮灭空中 + 2段·气动空中 + ·气动下落 + ·剑止万律"
    attr.add_effect(title, msg)

    crit_damage_total, expected_damage_total = 0.0, 0.0

    attr_copy = copy.deepcopy(attr)
    crit_damage, expected_damage = calc_damage_1(attr_copy, role, isGroup, FC="ThrumHavocMid-air")
    attr.add_effect("千声翻涌·湮灭空中3段", f"期望伤害:{crit_damage}; 暴击伤害:{expected_damage}")
    crit_damage_total += float(crit_damage.replace(",", ""))
    expected_damage_total += float(expected_damage.replace(",", ""))

    attr_copy = copy.deepcopy(attr)
    crit_damage, expected_damage = calc_damage_1(attr_copy, role, isGroup, FC="ThrumAeroMid-air")
    attr.add_effect("·气动空中3段+·气动下落", f"期望伤害:{crit_damage}; 暴击伤害:{expected_damage}")
    crit_damage_total += float(crit_damage.replace(",", ""))
    expected_damage_total += float(expected_damage.replace(",", ""))

    attr_copy = copy.deepcopy(attr)
    crit_damage, expected_damage = calc_damage_1(attr_copy, role, isGroup, FC="ThrumAeroSword")
    attr.add_effect("千声翻涌·剑止万律", f"期望伤害:{crit_damage}; 暴击伤害:{expected_damage}")
    crit_damage_total += float(crit_damage.replace(",", ""))
    expected_damage_total += float(expected_damage.replace(",", ""))

    return f"{crit_damage_total:,.0f}", f"{expected_damage_total:,.0f}"


damage_detail = [
    {
        "title": "超负荷",
        "func": lambda attr, role: calc_damage_1(attr, role, FC="Overshock"),
    },
    {
        "title": "最终战略",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "地面点按E-千声翻涌总伤",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "空中点按E-千声翻涌总伤",
        "func": lambda attr, role: calc_damage_4(attr, role),
    },
]

rank = damage_detail[0]
