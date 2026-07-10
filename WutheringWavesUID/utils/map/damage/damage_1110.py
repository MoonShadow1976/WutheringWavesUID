# 穗穗

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    cast_skill,
    cast_variation,
    heal_bonus,
    intro_skill_damage,
    skill_damage_calc,
)
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(heal_bonus)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    title = "润物"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "4", skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_healing_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    title = "穗穗-常态"
    msg = "特定攻击为命中目标附加【霜渐效应】"
    attr.set_env_glacio_chafe()
    attr.add_effect(title, msg)

    attr.set_phantom_dmg_bonus(needShuxing=False)

    chain_num = role.get_chain_num()
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "润物和春生造成的治疗量提升50%"
        attr.add_dmg_bonus(0.5, title, msg)

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    healing_bonus = attr.calculate_healing(attr.effect_life)

    crit_damage = f"{healing_bonus:,.0f}"
    return None, crit_damage


def calc_damage_2(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(heal_bonus)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    _role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    title = "翾舞"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "4", skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_healing_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    title = "穗穗-常态"
    msg = "特定攻击为命中目标附加【霜渐效应】"
    attr.set_env_glacio_chafe()
    attr.add_effect(title, msg)

    attr.set_phantom_dmg_bonus(needShuxing=False)

    _chain_num = role.get_chain_num()

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    healing_bonus = attr.calculate_healing(attr.effect_life)

    crit_damage = f"{healing_bonus:,.0f}"
    return None, crit_damage


def calc_damage_3(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    attr.set_char_damage(intro_skill_damage)
    attr.set_char_template("temp_life")

    role_name = role.role.roleName
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "变奏技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    title = "泠泠漱玉声"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "1", skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    damage_func = [cast_variation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # # 默认手法
    # title = "默认手法"
    # msg = "穗延奏(600芳菲信)-另角色获得烟岚延奏穗-穗变奏伤害"
    # attr.add_effect(title, msg)

    title = "穗穗-常态"
    msg = "特定攻击为命中目标附加【霜渐效应】"
    attr.set_env_glacio_chafe()
    attr.add_effect(title, msg)

    title = "穗穗-延奏技能"
    msg = "队伍中的角色全伤害加深25%"
    attr.add_dmg_deepen(0.25, title, msg)

    title = "穗穗-延奏-400芳菲信"
    value = min(0.002 * ((attr.energy_regen - 2) * 100 // 1), 0.12)
    msg = f"共鸣效率超200%每1%时提升0.2%伤害,上限12%,当前{value * 100:.2f}%"
    attr.add_dmg_bonus(value, title, msg)

    # title = "另角色烟岚延奏-600芳菲信"
    # value = min(0.001 * ((attr.energy_regen - 2) * 10000 // 12), 0.5)
    # msg = f"共鸣效率超200%每0.12%时提升0.1%攻击,上限50%,当前{value*100:.2f}%"
    # attr.add_atk_percent(value, title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-近水纳天光"
        msg = "该次攻击的暴击率提升80%"
        attr.add_crit_rate(0.8, title, msg)
        msg = "该次攻击造成的冷凝伤害提升240%"
        attr.add_dmg_bonus(2.4, title, msg)

    attr.set_phantom_dmg_bonus(needPhantom=False)

    chain_num = role.get_chain_num()
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "山河水境内触发效果的角色暴击伤害提升50%"
        attr.add_crit_dmg(0.5, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "变奏技能·泠泠漱玉声和共鸣技能·醒春潮的暴击伤害提升500%"
        attr.add_crit_dmg(5, title, msg)

    echo_damage(attr, isGroup)

    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


damage_detail = [
    {
        "title": "润物治疗量",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "翾舞治疗量",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "泠泠漱玉声伤害",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
]

rank = damage_detail[2]
