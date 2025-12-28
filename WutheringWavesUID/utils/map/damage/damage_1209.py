# 莫宁

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute, calc_percent_expression
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    cast_damage,
    cast_healing,
    cast_liberation,
    cast_skill,
    heal_bonus,
    liberation_damage,
    skill_create_healing,
    skill_damage_calc,
)
from .buff import lynae_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(heal_bonus)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_def")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "14", skillLevel)
    title = "分布式阵列治疗量"
    msg = f"技能倍率{skill_multi}"
    attr.add_healing_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 谐振场
    title = "共鸣回路-谐振场"
    msg = "谐振场生效范围内偏谐值累积效率提升50%"
    attr.add_off_tune_buildup_rate(0.5, title, msg)

    # 强谐振场
    title = "共鸣解放-强谐振场"
    msg = "强谐振场生效范围内附近队伍中所有角色防御提升20%"
    attr.add_def_percent(0.2, title, msg)

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "谐振场还会使偏谐值累积效率额外提升20%"
        attr.add_off_tune_buildup_rate(0.2, title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus(needShuxing=False)

    # 设置角色施放技能 - 增加偏谐值累积效率在前
    damage_func = [cast_healing, skill_create_healing]
    phase_damage(attr, role, damage_func, isGroup)

    echo_damage(attr, isGroup)

    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    healing_bonus = attr.calculate_healing(attr.effect_def)

    crit_damage = f"{healing_bonus:,.0f}"
    return None, crit_damage


def calc_damage_2(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(heal_bonus)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_def")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "27", skillLevel)
    title = "谐振场治疗量"
    msg = f"技能倍率{skill_multi}"
    attr.add_healing_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus(needShuxing=False)

    # 谐振场
    title = "共鸣回路-谐振场"
    msg = "谐振场生效范围内偏谐值累积效率提升50%"
    attr.add_off_tune_buildup_rate(0.5, title, msg)

    # 强谐振场
    title = "共鸣解放-强谐振场"
    msg = "强谐振场生效范围内附近队伍中所有角色防御提升20%"
    attr.add_def_percent(0.2, title, msg)

    title = "共鸣解放-强谐振场"
    msg = "继承谐振场的治疗效果，且治疗倍率提升40%"
    attr.add_skill_ratio_in_skill_description(0.4, title, msg)

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "谐振场还会使偏谐值累积效率额外提升20%"
        attr.add_off_tune_buildup_rate(0.2, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "强谐振场的治疗量提升30%"
        attr.add_dmg_bonus(0.32, title, msg)

    # 设置角色施放技能 - 增加偏谐值累积效率在前
    damage_func = [cast_healing]
    phase_damage(attr, role, damage_func, isGroup)

    echo_damage(attr, isGroup)

    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    healing_bonus = attr.calculate_healing(attr.effect_def)

    crit_damage = f"{healing_bonus:,.0f}"
    return None, crit_damage


def calc_damage_3(
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, Interfered: bool = False
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_def")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "21", skillLevel)
    title = "共鸣解放·临界协议"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 设置角色固有技能
    # role_breach = role.role.breach
    # if role_breach and role_breach >= 3:

    # 设置角色谐度破坏
    if Interfered:
        title = "解耦"
        msg = "莫宁于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        title = "解耦-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 临界协议
    if attr.energy_regen > 1:
        title = "共鸣解放-临界协议"
        dmg = min(0.8, (attr.energy_regen - 1) * 0.5)
        msg = f"共效超100%每1%为该伤害提升0.5%暴击,上限80%,当前提升{dmg * 100:.2f}%"
        attr.add_crit_rate(dmg, title, msg)
        dmg = min(1.6, attr.energy_regen - 1)
        msg = f"共效超100%每1%为该伤害提升1%爆伤,上限160%,当前提升{dmg * 100:.2f}%"
        attr.add_crit_dmg(dmg, title, msg)

    # 谐振场
    title = "共鸣回路-谐振场"
    msg = "谐振场生效范围内偏谐值累积效率提升50%"
    attr.add_off_tune_buildup_rate(0.5, title, msg)

    # 强谐振场
    title = "共鸣解放-强谐振场"
    msg = "强谐振场生效范围内附近队伍中所有角色防御提升20%"
    attr.add_def_percent(0.2, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()

    # 干涉标记
    if attr.energy_regen > 1 and (attr.is_env_shifting() or chain_num >= 1):
        title = "共鸣回路-干涉标记"
        dmg = min(0.4, (attr.energy_regen - 1) * 0.25)
        msg = f"共效超100%每1%计为0.25%伤害提升,上限40%,当前提升{dmg * 100:.2f}%"
        attr.add_dmg_bonus(dmg, title, msg)

    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%"
    attr.add_dmg_deepen(0.25, title, msg)

    if chain_num >= 2:
        if attr.energy_regen > 1:
            title = f"{role_name}-二链-干涉标记"
            dmg = min(0.32, (attr.energy_regen - 1) * 0.2)
            msg = f"共效超100%每1%提升0.2%爆伤,上限32%,当前提升{dmg * 100:.2f}%"
            attr.add_crit_dmg(dmg, title, msg)

        title = f"{role_name}-二链-谐振场"
        msg = "谐振场使偏谐值累积效率额外提升20%"
        attr.add_off_tune_buildup_rate(0.2, title, msg)

    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "共鸣解放·临界协议伤害倍率提升40%"
        attr.add_skill_ratio(0.4, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "共鸣解放·临界协议造成的伤害提升400%"
        attr.add_dmg_bonus(4, title, msg)

    # 设置角色施放技能 - 增加偏谐值累积效率在前 - 造成共鸣技能伤害吃火套
    damage_func = [cast_skill, cast_damage, cast_healing, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_def):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_def):,.0f}"
    return crit_damage, expected_damage


def calc_damage_10(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_def")

    # 琳奈buff
    lynae_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup)


def calc_damage_11(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_def")

    # 琳奈buff
    lynae_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, Interfered=True)


def calc_damage_12(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_def")

    # 琳奈buff
    lynae_buff(attr, 2, 5, isGroup)

    return calc_damage_3(attr, role, isGroup, Interfered=True)


damage_detail = [
    {
        "title": "分布式阵列治疗量",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "强谐振场治疗量",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "临界协议",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "响应集谐·临界协议",
        "func": lambda attr, role: calc_damage_3(attr, role, Interfered=True),
    },
    {
        "title": "0+1琳奈/临界协议",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "0+1琳奈/响应集谐·临界协议",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
    {
        "title": "2+5琳奈/响应集谐·临界协议",
        "func": lambda attr, role: calc_damage_12(attr, role),
    },
]

rank = damage_detail[2]
