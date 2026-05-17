# 达妮娅

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute, calc_percent_expression
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    cast_damage,
    cast_liberation,
    cast_skill,
    liberation_damage,
    skill_damage,
    skill_damage_calc,
)
from .buff import lupa_buff, lynae_buff, mornye_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    Interfered: bool = False,
    DarkCoreNum: int = 9,
    Mode: Literal["tune_strain", "fusion_burst"] = "fusion_burst",
    r: Literal["r_close", "r_open"] = "r_open",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)  # 默认共鸣解放伤害
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    chain_num = role.get_chain_num()

    title = "黯核"
    MaxDarkCoreNum = 3
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "【黯核】上限提升至5枚"
        MaxDarkCoreNum = 5
        attr.add_effect(title, msg)

    DarkCoreNum = min(DarkCoreNum, MaxDarkCoreNum)

    # 技能技能倍率
    if r == "r_close":
        if chain_num >= 3 and DarkCoreNum == MaxDarkCoreNum:
            title = f"{role_name}-三链"
            msg = "【黯核】数到上限时，技能伤害倍率增加1200%，视为共鸣解放伤害"
            attr.add_skill_ratio(12, title, msg)
        else:
            attr.set_char_damage(skill_damage)  # 共鸣技能伤害

        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "1", skillLevel)
        title = "拟态泡泡·布景之形"
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)
    else:
        if DarkCoreNum <= 0:
            attr.set_char_damage(skill_damage)  # 共鸣技能伤害
            skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "3", skillLevel)
            title = "轻唤·幻灭之形"
            msg = f"技能倍率{skill_multi}"
            attr.add_skill_multi(skill_multi, title, msg)
        else:
            skill_multi_1 = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "4", skillLevel)
            skill_multi_2 = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "5", skillLevel)
            title = "放逐·幻灭之形"
            skill_multi = f"{skill_multi_1}+{skill_multi_2}"
            msg = f"技能倍率{skill_multi}"
            attr.add_effect(title, msg)

            msg = f"放逐·幻灭之形第2段消耗所有【黯核】，伤害倍率提升 {DarkCoreNum}*150%"
            skill_multi_final = f"{skill_multi_1}+({skill_multi_2})*{DarkCoreNum}*150%"
            attr.add_skill_multi(skill_multi_final, title, msg)

    if Mode == "tune_strain":
        title = "共鸣模态·集谐"
        msg = "特定攻击为命中目标附加【集谐·偏移】"
        attr.set_env_tune_strain()
        attr.add_effect(title, msg)
    else:
        title = "共鸣模态·聚爆"
        msg = "特定攻击为命中目标附加【聚爆效应】"
        attr.set_env_fusion_burst()
        attr.add_effect(title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4 and r == "r_open":
        if Mode == "tune_strain":
            title = "固有技能·蚀刻繁彩-熵变强化时"
            msg = "共鸣模态·集谐:谐度破坏增幅提升10点"
            attr.add_tune_break_boost(10, title, msg)

            dmg = min(40, (attr.off_tune_buildup_rate - 1) * 100 // 10 * 8)
            msg = f"共鸣模态·集谐:偏累超100%每10%谐破提升8点,上限40点,当前{dmg:,.0f}点"
            attr.add_tune_break_boost(dmg, title, msg)
        else:
            title = "固有技能·蚀刻繁彩-熵变强化时"
            msg = "共鸣模态·聚爆:热熔伤害加成提升30%"
            attr.add_dmg_bonus(0.3, title, msg)

    # 共鸣解放
    if r == "r_open":
        title = "共鸣解放-熵变强化·幻灭之形"
        msg = "攻击提升30%"
        attr.add_atk_percent(0.3, title, msg)

    # 设置角色谐度破坏
    if Interfered and Mode == "tune_strain":
        title = "计时的溃灭"
        msg = "达妮娅于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        title = "计时的溃灭-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击伤害提升30%"
        attr.add_crit_dmg(0.3, title, msg)

    if chain_num >= 2:
        if Mode == "tune_strain":
            title = f"{role_name}-二链-集谐"
            msg = "谐度破坏增幅提升20点"
            attr.add_tune_break_boost(20, title, msg)
        else:
            title = f"{role_name}-二链-聚爆"
            msg = "热熔伤害加成提升50%"
            attr.add_dmg_bonus(0.5, title, msg)

            msg = "10层简并虚质使达妮娅造成伤害无视目标10%热熔伤害抗性"
            attr.add_enemy_resistance(-0.1, title, msg)

        if DarkCoreNum > 0 and r == "r_open":
            title = f"{role_name}-二链"
            msg = "共鸣技能放逐·幻灭之形伤害倍率提升40%"
            attr.add_skill_ratio(0.4, title, msg)

    if chain_num >= 6 and r == "r_open":
        title = f"{role_name}-六链"
        msg = "处于熵变强化时，攻击提升60%"
        attr.add_atk_percent(0.6, title, msg)
        msg = "处于熵变强化时，热熔伤害加成提升60%"
        attr.add_dmg_bonus(0.6, title, msg)

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
    Interfered: bool = False,
    Mode: Literal["tune_strain", "fusion_burst"] = "fusion_burst",
    r: Literal["r1", "r2"] = "r1",
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
    if r == "r1":
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "1", skillLevel)
        title = "帷幕终景·布景之形"
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)
    else:
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "2", skillLevel)
        title = "帷幕终景·幻灭之形"
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    if Mode == "tune_strain":
        title = "共鸣模态·集谐"
        msg = "特定攻击为命中目标附加【集谐·偏移】"
        attr.set_env_tune_strain()
        attr.add_effect(title, msg)
    else:
        title = "共鸣模态·聚爆"
        msg = "特定攻击为命中目标附加【聚爆效应】"
        attr.set_env_fusion_burst()
        attr.add_effect(title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        if Mode == "tune_strain":
            title = "固有技能·蚀刻繁彩"
            msg = "共鸣模态·集谐:谐度破坏增幅提升10点"
            attr.add_tune_break_boost(10, title, msg)

            dmg = min(40, (attr.off_tune_buildup_rate - 1) * 100 // 10 * 8)
            msg = f"共鸣模态·集谐:偏累超100%每10%谐破提升8点,上限40点,当前{dmg:,.0f}点"
            attr.add_tune_break_boost(dmg, title, msg)
        else:
            title = "固有技能·蚀刻繁彩"
            msg = "共鸣模态·聚爆:热熔伤害加成提升30%"
            attr.add_dmg_bonus(0.3, title, msg)

    # 共鸣解放 都能吃到
    title = "共鸣解放-熵变强化·幻灭之形"
    msg = "攻击提升30%"
    attr.add_atk_percent(0.3, title, msg)

    # 设置角色谐度破坏
    if Interfered and Mode == "tune_strain":
        title = "计时的溃灭"
        msg = "达妮娅于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        title = "计时的溃灭-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击伤害提升30%"
        attr.add_crit_dmg(0.3, title, msg)

    if chain_num >= 2:
        if Mode == "tune_strain":
            title = f"{role_name}-二链-集谐"
            msg = "谐度破坏增幅提升20点"
            attr.add_tune_break_boost(20, title, msg)
        else:
            title = f"{role_name}-二链-聚爆"
            msg = "热熔伤害加成提升50%"
            attr.add_dmg_bonus(0.5, title, msg)

            msg = "10层简并虚质使达妮娅造成伤害无视目标10%热熔伤害抗性"
            attr.add_enemy_resistance(-0.1, title, msg)

    if chain_num >= 3:
        if r == "r2":
            title = f"{role_name}-三链"
            msg = "共鸣解放帷幕终景·幻灭之形伤害倍率提升80%"
            attr.add_skill_ratio(0.8, title, msg)

    if chain_num >= 5:
        if r == "r1":
            title = f"{role_name}-五链"
            msg = "共鸣解放帷幕终景·布景之形造成的伤害提升100%"
            attr.add_dmg_bonus(1, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "处于熵变强化时，攻击提升60%"
        attr.add_atk_percent(0.6, title, msg)
        msg = "处于熵变强化时，热熔伤害加成提升60%"
        attr.add_dmg_bonus(0.6, title, msg)

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
    Interfered: bool = False,
    Mode: Literal["tune_strain", "fusion_burst"] = "fusion_burst",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "1", skillLevel)
    title = "蚀域每次伤害"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    if Mode == "tune_strain":
        title = "共鸣模态·集谐"
        msg = "特定攻击为命中目标附加【集谐·偏移】"
        attr.set_env_tune_strain()
        attr.add_effect(title, msg)
    else:
        title = "共鸣模态·聚爆"
        msg = "特定攻击为命中目标附加【聚爆效应】"
        attr.set_env_fusion_burst()
        attr.add_effect(title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 设置角色固有技能
    # role_breach = role.role.breach
    # if role_breach and role_breach >= 4:

    # 设置角色谐度破坏
    if Interfered and Mode == "tune_strain":
        title = "计时的溃灭"
        msg = "达妮娅于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        title = "计时的溃灭-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击伤害提升30%"
        attr.add_crit_dmg(0.3, title, msg)

    if chain_num >= 2:
        if Mode == "tune_strain":
            title = f"{role_name}-二链-集谐"
            msg = "谐度破坏增幅提升20点"
            attr.add_tune_break_boost(20, title, msg)
        else:
            title = f"{role_name}-二链-聚爆"
            msg = "热熔伤害加成提升50%"
            attr.add_dmg_bonus(0.5, title, msg)

            msg = "10层简并虚质使达妮娅造成伤害无视目标10%热熔伤害抗性"
            attr.add_enemy_resistance(-0.1, title, msg)

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
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_atk")

    title = "共鸣模态·集谐"
    msg = "特定攻击为命中目标附加【集谐·偏移】"
    attr.set_env_tune_rupture()

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 琳奈buff
    lynae_buff(attr, 0, 1, isGroup)

    return calc_damage_1(attr, role, isGroup, True, Mode="tune_strain")


def calc_damage_11(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = True,
) -> tuple[str, str]:
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 露帕buff
    lupa_buff(attr, 0, 1, isGroup)

    return calc_damage_1(attr, role, isGroup, Mode="fusion_burst")


damage_detail = [
    {
        "title": "帷幕终景·布景之形(聚爆)",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "放逐·幻灭之形(聚爆-满核)",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "放逐·幻灭之形(响应集谐-满核)",
        "func": lambda attr, role: calc_damage_1(attr, role, Interfered=True, Mode="tune_strain"),
    },
    {
        "title": "帷幕终景·幻灭之形(聚爆)",
        "func": lambda attr, role: calc_damage_2(attr, role, r="r2"),
    },
    {
        "title": "拟态泡泡·布景之形(聚爆-满核)",
        "func": lambda attr, role: calc_damage_1(attr, role, r="r_close"),
    },
    {
        "title": "蚀域每次伤害(聚爆)",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "01莫/01露/放逐·(聚爆-满核)",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
    {
        "title": "01莫/01琳/放逐·(响应集谐-满核)",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
]

rank = damage_detail[1]
