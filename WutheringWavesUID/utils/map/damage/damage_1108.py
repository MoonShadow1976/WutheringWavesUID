# 绯雪
import copy

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    add_comma_separated_numbers,
    attack_damage,
    cast_attack,
    cast_hit,
    cast_liberation,
    cast_skill,
    liberation_damage,
    skill_damage,
    skill_damage_calc,
)
from .buff import shouanren_buff, zhezhi_buff
from .damage import echo_damage, phase_damage, weapon_damage


def _common_setup(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False):
    """绯雪通用设置：固有技能·细雪、共鸣链额外通用增益等。"""
    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 固有技能·细雪 (雪锈) - 自身为登场角色时持续生效
    # 1层：自身造成的霜冻效应伤害加深30%，绯雪暴击伤害提升40%
    title = f"{role_name}-固有技能-细雪-1层雪锈"
    msg = "自身暴击伤害提升40%"
    attr.add_crit_dmg(0.4, title, msg)

    # 6链：持有2层雪锈时绯雪暴击伤害额外提升40%
    if chain_num >= 6:
        title = f"{role_name}-六链-2层雪锈"
        msg = "绯雪暴击伤害提升40%"
        attr.add_crit_dmg(0.4, title, msg)

    return role_name, chain_num


def calc_damage_1(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> (str, str):
    """重击·寒簇·常世身伤害 (常世身蓄力重击，伤害结算为共鸣解放伤害)"""
    # 设置角色伤害类型 (此次伤害为共鸣解放伤害)
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    title = "默认手法"
    if isGroup:
        msg = "变奏入场 ee aa 蓄力重击·寒簇"
    else:
        msg = "ee aa 蓄力重击·寒簇"
    attr.add_effect(title, msg)

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "常态攻击"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率 (skillTree["1"]["level"]["105"])
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "105", skillLevel)
    title = "重击·寒簇·常世身"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_skill, cast_hit]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 通用设置
    role_name, chain_num = _common_setup(attr, role, isGroup)

    # 共鸣链
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "重击·寒簇·常世身的伤害倍率提升160%"
        attr.add_skill_ratio(1.6, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_2(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> (str, str):
    """预求我身·见心伤害 (常世身->预求身切换的共鸣解放)"""
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板
    attr.set_char_template("temp_atk")

    title = "默认手法"
    if isGroup:
        msg = "变奏入场 ee aa 蓄力 q (预求我身·见心)"
    else:
        msg = "ee aa 蓄力 q (预求我身·见心)"
    attr.add_effect(title, msg)

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率 (skillTree["3"]["level"]["22"])
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "22", skillLevel)
    title = "预求我身·见心"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_skill, cast_hit, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 通用设置
    role_name, chain_num = _common_setup(attr, role, isGroup)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 共鸣链
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "预求我身·见心造成的暴击伤害提升500%"
        attr.add_crit_dmg(5.0, title, msg)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_3(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, stack: int = 3) -> (str, str):
    """预求我身·归刃伤害 (默认满3层【锻雪·归刃】)"""
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板
    attr.set_char_template("temp_atk")

    title = "默认手法"
    if isGroup:
        msg = f"变奏入场 q (预求我身·归刃·{stack}层锻雪)"
    else:
        msg = f"q (预求我身·归刃·{stack}层锻雪)"
    attr.add_effect(title, msg)

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 基础倍率 (skillTree["3"]["level"]["23"])
    base_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "23", skillLevel)
    # 每点【锻雪·归刃】增加 (skillTree["3"]["level"]["24"])
    per_stack_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "24", skillLevel)

    title = "预求我身·归刃-基础倍率"
    msg = f"技能倍率{base_multi}"
    attr.add_skill_multi(base_multi, title, msg)

    if stack > 0:
        title = f"预求我身·归刃-{stack}层锻雪加成"
        msg = f"每点锻雪·归刃增加{per_stack_multi}, 共{stack}点"
        # 拼接 stack 倍数的倍率字符串 e.g. "400.00%+400.00%+400.00%"
        stack_expr = "+".join([per_stack_multi] * stack)
        attr.add_skill_multi(stack_expr, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_skill, cast_hit, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 通用设置
    role_name, chain_num = _common_setup(attr, role, isGroup)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 共鸣链
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "预求我身·归刃造成的暴击伤害提升500%"
        attr.add_crit_dmg(5.0, title, msg)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_4(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> (str, str):
    """重击·枯霜·预求身伤害 (预求身蓄力重击，伤害结算为共鸣解放伤害)"""
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板
    attr.set_char_template("temp_atk")

    title = "默认手法"
    if isGroup:
        msg = "变奏入场 q aa 蓄力 重击·枯霜·预求身"
    else:
        msg = "q aa 蓄力 重击·枯霜·预求身"
    attr.add_effect(title, msg)

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "常态攻击"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率 (skillTree["1"]["level"]["114"])
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "114", skillLevel)
    title = "重击·枯霜·预求身"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_skill, cast_hit, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 通用设置
    role_name, chain_num = _common_setup(attr, role, isGroup)

    # 共鸣链
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "重击·预求身的伤害倍率提升120%"
        attr.add_skill_ratio(1.2, title, msg)

    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "重击·枯霜·预求身的伤害倍率提升160%"
        attr.add_skill_ratio(1.6, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_5(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> (str, str):
    """普攻·居合伤害 (居合架势下的普攻终结技)"""
    # 设置角色伤害类型 (普攻类)
    attr.set_char_damage(attack_damage)
    # 设置角色模板
    attr.set_char_template("temp_atk")

    title = "默认手法"
    if isGroup:
        msg = "变奏入场 q ... 普攻·居合"
    else:
        msg = "q ... 普攻·居合"
    attr.add_effect(title, msg)

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率 (skillTree["7"]["level"]["28"])
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "28", skillLevel)
    title = "普攻·居合"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_skill, cast_hit, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 通用设置
    role_name, chain_num = _common_setup(attr, role, isGroup)

    # 共鸣链
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "普攻·居合的伤害倍率提升125%"
        attr.add_skill_ratio(1.25, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_6(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> (str, str):
    """共鸣技能·霜罚·白玉切伤害"""
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板
    attr.set_char_template("temp_atk")

    title = "默认手法"
    if isGroup:
        msg = "变奏入场 q e (霜罚·白玉切)"
    else:
        msg = "q e (霜罚·白玉切)"
    attr.add_effect(title, msg)

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率 (skillTree["2"]["level"]["20"])
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "20", skillLevel)
    title = "霜罚·白玉切"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_skill, cast_hit, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 通用设置
    role_name, chain_num = _common_setup(attr, role, isGroup)

    # 共鸣链
    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "霜罚·白玉切的伤害倍率提升80%"
        attr.add_skill_ratio(0.8, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> (str, str):
    """绯雪一套循环总伤害 (重击·寒簇 + 见心 + 归刃·3层锻雪)"""
    title = "默认手法"
    if isGroup:
        msg = "变奏入场 ee aa 蓄力重击·寒簇 q(见心) -> 预求身 q(归刃·3层锻雪)"
    else:
        msg = "ee aa 蓄力重击·寒簇 q(见心) -> 预求身 q(归刃·3层锻雪)"

    attr.add_effect(title, msg)
    init_len = len(attr.effect)

    attr1 = copy.deepcopy(attr)
    crit_damage1, expected_damage1 = calc_damage_1(attr1, role, isGroup)
    attr1.add_effect("重击·寒簇·常世身伤害", f"期望伤害:{crit_damage1}; 暴击伤害:{expected_damage1}")

    attr2 = copy.deepcopy(attr)
    crit_damage2, expected_damage2 = calc_damage_2(attr2, role, isGroup)
    attr2.add_effect("预求我身·见心伤害", f"期望伤害:{crit_damage2}; 暴击伤害:{expected_damage2}")

    attr3 = copy.deepcopy(attr)
    crit_damage3, expected_damage3 = calc_damage_3(attr3, role, isGroup)
    attr3.add_effect("预求我身·归刃伤害(3层锻雪)", f"期望伤害:{crit_damage3}; 暴击伤害:{expected_damage3}")

    crit_damage = add_comma_separated_numbers(crit_damage1, crit_damage2, crit_damage3)
    expected_damage = add_comma_separated_numbers(expected_damage1, expected_damage2, expected_damage3)

    attr.add_effect(" ", " ")
    attr.effect.extend(attr1.effect[init_len + 1 :])
    attr.add_effect(" ", " ")
    attr.effect.extend(attr2.effect[init_len + 1 :])
    attr.add_effect(" ", " ")
    attr.effect.extend(attr3.effect[init_len + 1 :])

    return crit_damage, expected_damage


def calc_damage_10(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> (str, str):
    """0+1守/0折枝/归刃伤害"""
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_atk")

    # 守岸人buff
    shouanren_buff(attr, 0, 1, isGroup)

    # 折枝buff
    zhezhi_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup)


def calc_damage_11(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> (str, str):
    """6+5守/6折/归刃伤害"""
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_atk")

    # 守岸人buff
    shouanren_buff(attr, 6, 5, isGroup)

    # 折枝buff
    zhezhi_buff(attr, 6, 1, isGroup)

    return calc_damage_3(attr, role, isGroup)


damage_detail = [
    {
        "title": "重击·寒簇·常世身伤害",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "预求我身·见心伤害",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "预求我身·归刃伤害(3层锻雪)",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "重击·枯霜·预求身伤害",
        "func": lambda attr, role: calc_damage_4(attr, role),
    },
    {
        "title": "普攻·居合伤害",
        "func": lambda attr, role: calc_damage_5(attr, role),
    },
    {
        "title": "霜罚·白玉切伤害",
        "func": lambda attr, role: calc_damage_6(attr, role),
    },
    {
        "title": "一套循环总伤害",
        "func": lambda attr, role: calc_damage(attr, role),
    },
    {
        "title": "0+1守/0折/归刃伤害",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "6+5守/6折/归刃伤害",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
]

rank = damage_detail[6]
