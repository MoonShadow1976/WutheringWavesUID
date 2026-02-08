# 爱弥斯

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    Fusion_Burst_Role_Ids,
    SkillTreeMap,
    SkillType,
    Tune_Rupture_Role_Ids,
    cast_damage,
    cast_liberation,
    cast_skill,
    liberation_damage,
    skill_damage_calc,
)
from .buff import lynae_buff, mornye_buff
from .damage import echo_damage, phase_damage, weapon_damage


def get_role_num(
    attr: DamageAttribute,
    char_id_list: list[int],
):
    """
    获取队伍中符合要求的角色数量
        char_id_list: 角色ID列表
    """
    num = 1
    for char_id in attr.teammate_char_ids:
        if int(char_id) in char_id_list:
            num += 1
    return num


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    Interfered: bool = False,
    Mode: Literal["tune_rupture", "fusion_burst"] = "tune_rupture",
    SeraphicDuet: Literal["Encore", "Overture"] = "Encore",
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
    skillParamId = "1" if SeraphicDuet == "Encore" else "2"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    title = "共鸣技能·光翼共奏·登台" if SeraphicDuet == "Encore" else "共鸣技能·光翼共奏·降临"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    if Mode == "tune_rupture":
        title = "共鸣模态·震谐"
        msg = "特定攻击为命中目标附加【震谐·偏移】"
        attr.set_env_tune_rupture()
        attr.add_effect(title, msg)
    else:
        title = "共鸣模态·聚爆"
        msg = "特定攻击为命中目标附加【聚爆效应】"
        attr.set_env_fusion_burst()
        attr.add_effect(title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        if chain_num >= 3:
            title = f"{role_name}-三链-固有技能替换"
            msg = "爱弥斯暴击伤害提升80%"
            attr.add_crit_dmg(0.8, title, msg)
        elif Mode == "tune_rupture":
            title = "固有技能·星与星之间"
            role_num = get_role_num(attr, Tune_Rupture_Role_Ids)
            msg = f"共鸣模态·震谐:爱弥斯暴击伤害提升20%，叠加{role_num}层"
            attr.add_crit_dmg(0.2 * role_num, title, msg)
        else:
            title = "固有技能·星与星之间"
            role_num = get_role_num(attr, Fusion_Burst_Role_Ids)
            msg = f"共鸣模态·聚爆:爱弥斯暴击伤害提升30%，叠加{role_num}层"
            attr.add_crit_dmg(0.3 * role_num, title, msg)

    # 设置角色谐度破坏
    # if Interfered:

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 2:
        title = f"{role_name}-二链"
        tip = "登台" if SeraphicDuet == "Encore" else "降临"
        msg = f"共鸣技能光翼共奏·{tip}的伤害倍率提升100%"
        attr.add_skill_ratio(1.0, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到爱弥斯的共鸣解放伤害提升40%"
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
    Interfered: bool = False,
    Mode: Literal["tune_rupture", "fusion_burst"] = "tune_rupture",
    HeavenfallEdict: Literal["Overdrive", "Finale"] = "Overdrive",
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
    skillParamId = "1" if HeavenfallEdict == "Overdrive" else "2"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    title = "星辉破界而来·过载" if HeavenfallEdict == "Overdrive" else "星辉破界而来·终结"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    if Mode == "tune_rupture":
        title = "共鸣模态·震谐"
        msg = "特定攻击为命中目标附加【震谐·偏移】"
        attr.set_env_tune_rupture()
        attr.add_effect(title, msg)
    else:
        title = "共鸣模态·聚爆"
        msg = "特定攻击为命中目标附加【聚爆效应】"
        attr.set_env_fusion_burst()
        attr.add_effect(title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        if chain_num >= 3:
            title = f"{role_name}-三链-固有技能替换"
            msg = "爱弥斯暴击伤害提升60%"
            attr.add_crit_dmg(0.6, title, msg)
            if HeavenfallEdict == "Finale":
                msg = "共鸣解放星辉破界而来·终结伤害加深25%"
                attr.add_dmg_deepen(0.25, title, msg)
        elif Mode == "tune_rupture":
            title = "固有技能·星与星之间"
            role_num = get_role_num(attr, Tune_Rupture_Role_Ids)
            msg = f"共鸣模态·震谐:爱弥斯暴击伤害提升20%，叠加{role_num}层"
            attr.add_crit_dmg(0.2 * role_num, title, msg)
            if role_num >= 3 and HeavenfallEdict == "Finale":
                msg = "达到3层时，星辉破界而来·终结伤害加深25%"
                attr.add_dmg_deepen(0.25, title, msg)
        else:
            title = "固有技能·星与星之间"
            role_num = get_role_num(attr, Fusion_Burst_Role_Ids)
            msg = f"共鸣模态·聚爆:爱弥斯暴击伤害提升30%，叠加{role_num}层"
            attr.add_crit_dmg(0.3 * role_num, title, msg)
            if role_num >= 2 and HeavenfallEdict == "Finale":
                msg = "达到2层时，星辉破界而来·终结伤害加深25%"
                attr.add_dmg_deepen(0.25, title, msg)

    # 设置角色谐度破坏
    # if Interfered:

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 3:
        title = f"{role_name}-三链"
        tip = "过载" if HeavenfallEdict == "Overdrive" else "终结"
        skill_ratio = 0.4 if HeavenfallEdict == "Overdrive" else 1
        msg = f"共鸣解放星辉破界而来·{tip}的伤害倍率提升{skill_ratio * 100}%"
        attr.add_skill_ratio(skill_ratio, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到爱弥斯的共鸣解放伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置角色施放技能
    damage_func = [cast_damage, cast_liberation]
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
    Mode: Literal["tune_rupture", "fusion_burst"] = "tune_rupture",
    HeavenfallEdict: Literal["Overdrive", "Finale"] = "Overdrive",
) -> tuple[str, str]:
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 琳奈buff
    lynae_buff(attr, 0, 1, isGroup)

    return calc_damage_2(attr, role, isGroup, False, Mode, HeavenfallEdict)


damage_detail = [
    {
        "title": "光翼共奏·登台(震谐)",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "光翼共奏·降临(震谐)",
        "func": lambda attr, role: calc_damage_1(attr, role, SeraphicDuet="Overture"),
    },
    {
        "title": "星辉破界而来·过载(震谐)",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "星辉破界而来·终结(震谐)",
        "func": lambda attr, role: calc_damage_2(attr, role, HeavenfallEdict="Finale"),
    },
    {
        "title": "星辉破界而来·终结(聚爆)",
        "func": lambda attr, role: calc_damage_2(attr, role, Mode="fusion_burst", HeavenfallEdict="Finale"),
    },
    {
        "title": "01莫/01琳/星辉破界而来·终结",
        "func": lambda attr, role: calc_damage_10(attr, role, HeavenfallEdict="Finale"),
    },
]

rank = damage_detail[3]
