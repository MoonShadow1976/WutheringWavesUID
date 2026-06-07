# 露西

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
    hit_damage,
    skill_damage_calc,
)
from .buff import mornye_buff, motefei_buff, rebecca_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "4", skillLevel)
    title = "共鸣技能·死锁"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加骇破·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()
    attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        title = "固有技能-进程破解-网络后门"
        msg = "叠加至2层时，总共获得全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)

    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "附加以下欺骗程式"
        attr.add_effect(title, msg)

        # 共鸣解放
        title = "欺骗程式·义体故障"
        msg = "使所有标记目标受到伤害提升5%"
        attr.add_dmg_bonus(0.05, title, msg)

        title = "欺骗程式·突破协议"
        msg = "使所有标记目标降低5%的防御"
        attr.add_defense_reduction(0.05, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "施放变奏技能·过时幻觉时攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "附加【骇破·偏移】后，全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "【骇破】效果下的目标受到露西的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置角色施放技能
    damage_func = [cast_skill, cast_damage, cast_liberation]
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
    z: Literal["z2", "z3"] = "z3",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "常态攻击"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    if z == "z2":
        title = "重击·双线程"
        skillParamId = "16"
    else:
        title = "重击·多线程"
        skillParamId = "17"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    chain_num = role.get_chain_num()
    if z == "z3":
        title = "共鸣回路-持有SQL"
        dmg = 2.7
        if chain_num >= 2:
            title = "共鸣回路-二链-持有SQL"
            dmg = 5.6
        msg = f"本次伤害倍率提升{dmg * 100:,.0f}%并移除SQL标记"
        attr.add_skill_ratio_in_skill_description(dmg, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加骇破·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()
    attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        title = "固有技能-进程破解-网络后门"
        msg = "叠加至2层时，总共获得全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)

    # 共鸣回路
    title = "共鸣回路-算法压缩"
    msg = "自身衍射伤害加成提升65%"
    attr.add_dmg_bonus(0.65, title, msg)

    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "附加以下欺骗程式"
        attr.add_effect(title, msg)

        # 共鸣解放
        title = "欺骗程式·义体故障"
        msg = "使所有标记目标受到伤害提升5%"
        attr.add_dmg_bonus(0.05, title, msg)

        title = "欺骗程式·突破协议"
        msg = "使所有标记目标降低5%的防御"
        attr.add_defense_reduction(0.05, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "施放变奏技能·过时幻觉时攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "附加【骇破·偏移】后，全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "【骇破】效果下的目标受到露西的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置角色施放技能
    damage_func = [cast_skill, cast_damage, cast_liberation]
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
    r: Literal["r1", "r2"] = "r2",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    if r == "r1":
        title = "共鸣解放·网络行者·覆写篡改"
        skillParamId = "1"
    else:
        title = "共鸣解放·暗网深潜·覆写篡改"
        skillParamId = "5"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加骇破·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()
    attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        title = "固有技能-进程破解-网络后门"
        msg = "叠加至2层时，总共获得全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)

    # 共鸣回路
    title = "共鸣回路-算法压缩"
    msg = "自身衍射伤害加成提升65%"
    attr.add_dmg_bonus(0.65, title, msg)

    # 共鸣解放
    title = "欺骗程式·义体故障"
    msg = "使所有标记目标受到伤害提升5%"
    attr.add_dmg_bonus(0.05, title, msg)

    title = "欺骗程式·突破协议"
    msg = "使所有标记目标降低5%的防御"
    attr.add_defense_reduction(0.05, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "施放变奏技能·过时幻觉时攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "共鸣解放覆写篡改的伤害倍率提升50%"
        attr.add_skill_ratio(0.5, title, msg)
        msg = "共鸣解放覆写篡改的暴击伤害提升100%"
        attr.add_crit_dmg(1, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "附加【骇破·偏移】后，全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "【骇破】效果下的目标受到露西的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置角色施放技能
    damage_func = [cast_skill, cast_damage, cast_liberation]
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


def calc_damage_10(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = True,
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    title = "露西-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()

    # 莫宁buff
    mornye_buff(attr, 1, 1, isGroup)

    # 莫特斐buff
    motefei_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, r="r2")


def calc_damage_11(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = True,
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    title = "露西-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()

    # 莫宁buff
    mornye_buff(attr, 1, 1, isGroup)

    # 丽贝卡buff
    rebecca_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, r="r2")


damage_detail = [
    {
        "title": "共鸣技能·死锁",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "重击·双线程",
        "func": lambda attr, role: calc_damage_2(attr, role, z="z2"),
    },
    {
        "title": "重击·多线程",
        "func": lambda attr, role: calc_damage_2(attr, role, z="z3"),
    },
    {
        "title": "共鸣解放·网络行者·覆写篡改",
        "func": lambda attr, role: calc_damage_3(attr, role, r="r1"),
    },
    {
        "title": "共鸣解放·暗网深潜·覆写篡改",
        "func": lambda attr, role: calc_damage_3(attr, role, r="r2"),
    },
    {
        "title": "11莫/01莫/·暗网深潜·",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "11莫/01丽/·暗网深潜·",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
]

rank = damage_detail[4]
