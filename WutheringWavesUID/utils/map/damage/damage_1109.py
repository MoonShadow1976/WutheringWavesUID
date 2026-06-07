# 洛瑟菈

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    attack_damage,
    cast_damage,
    cast_liberation,
    cast_skill,
    phantom_damage,
    skill_damage,
    skill_damage_calc,
)
from .buff import qiuyuan_buff, shouanren_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    Mode: Literal["glacio_chafe", "echo"] = "glacio_chafe",
    e: Literal["e_compensate", "e_spotlight"] = "e_spotlight",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    if e == "e_compensate":
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "9", skillLevel)
        title = "补光"
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)
    else:
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "10", skillLevel)
        title = "追光"
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    if Mode == "glacio_chafe":
        # 附加霜渐效应
        title = f"{role_name}-常态"
        msg = "特定攻击为命中目标附加【霜渐效应】"
        attr.set_env_glacio_chafe()
        attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        if e == "e_spotlight":
            if Mode == "glacio_chafe":
                title = "固有技能·慢镜头-霜渐模态"
                msg = "队伍中登场角色一定范围内的目标冷凝抗性降低8%"
                attr.add_enemy_resistance(-0.08, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1 and e == "e_spotlight":
        title = f"{role_name}-一链"
        msg = "施放共鸣技能·追光时，洛瑟菈的暴击提升20%"
        attr.add_crit_rate(0.2, title, msg)

    # 四链加攻吃不到

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
    Mode: Literal["glacio_chafe", "echo"] = "glacio_chafe",
    r: Literal["r", "a3", "LetItGo"] = "r",
) -> tuple[str, str]:
    # 设置角色伤害类型
    # 强化a3是普攻伤害，其他两个根据模态变化
    if r == "a3" or Mode == "glacio_chafe":
        attr.set_char_damage(attack_damage)
    else:
        attr.set_char_damage(phantom_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    if r == "r":
        title = "历历在目"
        skillParamId = "13"
    elif r == "a3":
        title = "普攻·溯念留形第三段"
        skillParamId = "16"
    else:
        title = "断舍离"
        skillParamId = "17"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    if Mode == "glacio_chafe":
        # 附加霜渐效应
        title = f"{role_name}-常态"
        msg = "特定攻击为命中目标附加【霜渐效应】"
        attr.set_env_glacio_chafe()
        attr.add_effect(title, msg)

    zoom_count = 0  # 变焦层数

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        if Mode == "glacio_chafe":
            title = "固有技能·慢镜头-霜渐模态"
            msg = "队伍中登场角色一定范围内的目标冷凝抗性降低8%"
            attr.add_enemy_resistance(-0.08, title, msg)
        else:
            title = "固有技能·慢镜头-声骸模态"
            msg = "队伍中的角色声骸技能伤害加成提升25%"
            attr.add_dmg_bonus(0.25, title, msg)

    if role_breach and role_breach >= 4:
        if Mode == "echo" and r != "r":
            if r == "a3":
                zoom_count += 1 * 1.5
                msg = "普攻第3段期间同时消耗【照片】，整体平均获得1.5层变焦"
            else:
                zoom_count += 1 * 3
                msg = "消耗三张【照片】，获得3层变焦"
            title = "固有技能·铭记-声骸模态"
            attr.add_effect(title, msg)

    # 共鸣解放
    if Mode == "glacio_chafe":
        title = "共鸣解放-追忆状态-霜渐模态"
        msg = "施放该技能时普攻伤害加成提升30%"
        attr.add_dmg_bonus(0.3, title, msg)
    else:
        title = "共鸣解放-追忆状态-声骸模态"
        msg = "施放该技能时声骸技能伤害加成提升30%"
        attr.add_dmg_bonus(0.3, title, msg)

        zoom_count += 1
        title = "共鸣回路-声骸模态"
        msg = "施放共鸣解放·历历在目时获得1层变焦"
        attr.add_effect(title, msg)

    # 变焦buff
    if Mode == "echo" and zoom_count > 0:
        title = "变焦"
        msg = f"{zoom_count}层变焦使角色声骸技能伤害的暴击伤害提升{zoom_count * 10}%"
        attr.add_crit_dmg(zoom_count * 0.1, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "施放共鸣技能·追光时，洛瑟菈的暴击提升20%"
        attr.add_crit_rate(0.2, title, msg)

    if chain_num >= 2 and Mode == "echo":
        title = f"{role_name}-二链-声骸模态"
        msg = "队伍中角色的声骸技能伤害加成提升40%"
        attr.add_dmg_bonus(0.4, title, msg)

    if chain_num >= 3 and r == "LetItGo":
        title = f"{role_name}-三链"
        msg = "断舍离的伤害倍率提升100%"
        attr.add_skill_ratio(1, title, msg)

    if chain_num >= 4 and r != "r":
        title = f"{role_name}-四链"
        if r == "a3":
            msg = "普攻第3段期间同时施放遗忘，攻击整体平均提升15%"
            attr.add_atk_percent(0.15, title, msg)
        else:
            msg = "施放三次遗忘时，攻击提升30%"
            attr.add_atk_percent(0.3, title, msg)

    if chain_num >= 6 and r == "LetItGo":
        title = f"{role_name}-六链"
        msg = "消耗三张【照片】，使断舍离造成的伤害提升600%"
        attr.add_dmg_bonus(6, title, msg)

    # 设置角色施放技能
    damage_func = [cast_skill, cast_damage]
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
    Mode: Literal["glacio_chafe", "echo"] = "glacio_chafe",
    photo_count: int = 0,
) -> tuple[str, str]:
    # 设置角色伤害类型
    if Mode == "glacio_chafe":
        attr.set_char_damage(attack_damage)
    else:
        attr.set_char_damage(phantom_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "27", skillLevel)
    title = "遗忘"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    if Mode == "glacio_chafe":
        # 附加霜渐效应
        title = f"{role_name}-常态"
        msg = "特定攻击为命中目标附加【霜渐效应】"
        attr.set_env_glacio_chafe()
        attr.add_effect(title, msg)

    zoom_count = 0  # 变焦层数

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        if Mode == "glacio_chafe":
            title = "固有技能·慢镜头-霜渐模态"
            msg = "队伍中登场角色一定范围内的目标冷凝抗性降低8%"
            attr.add_enemy_resistance(-0.08, title, msg)
        else:
            title = "固有技能·慢镜头-声骸模态"
            msg = "队伍中的角色声骸技能伤害加成提升25%"
            attr.add_dmg_bonus(0.25, title, msg)

    if role_breach and role_breach >= 4:
        if Mode == "echo":
            zoom_count += 1 * photo_count
            msg = f"消耗{photo_count}张【照片】，获得{photo_count}层变焦"
            title = "固有技能·铭记-声骸模态"
            attr.add_effect(title, msg)

    # 共鸣解放
    if Mode == "glacio_chafe":
        title = "共鸣解放-追忆状态-霜渐模态"
        msg = "施放该技能时普攻伤害加成提升30%"
        attr.add_dmg_bonus(0.3, title, msg)
    else:
        title = "共鸣解放-追忆状态-声骸模态"
        msg = "施放该技能时声骸技能伤害加成提升30%"
        attr.add_dmg_bonus(0.3, title, msg)

        zoom_count += 1
        title = "共鸣回路-声骸模态"
        msg = "施放共鸣解放·历历在目时获得1层变焦"
        attr.add_effect(title, msg)

    # 变焦buff
    if Mode == "echo" and zoom_count > 0:
        title = "变焦"
        msg = f"{zoom_count}层变焦使角色声骸技能伤害的暴击伤害提升{zoom_count * 10}%"
        attr.add_crit_dmg(zoom_count * 0.1, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "施放共鸣技能·追光时，洛瑟菈的暴击提升20%"
        attr.add_crit_rate(0.2, title, msg)

    if chain_num >= 2 and Mode == "echo":
        title = f"{role_name}-二链-声骸模态"
        msg = "队伍中角色的声骸技能伤害加成提升40%"
        attr.add_dmg_bonus(0.4, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = f"施放{photo_count}次遗忘时，攻击提升{photo_count * 10}%"
        attr.add_atk_percent(0.1 * photo_count, title, msg)

    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "遗忘的伤害倍率提升50%"
        attr.add_skill_ratio(0.5, title, msg)

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
    Mode: Literal["glacio_chafe", "echo"] = "echo",
    r: Literal["r", "a3", "LetItGo"] = "LetItGo",
) -> tuple[str, str]:
    # 设置角色伤害类型
    # 强化a3是普攻伤害，其他两个根据模态变化
    if r == "a3" or Mode == "glacio_chafe":
        attr.set_char_damage(attack_damage)
    else:
        attr.set_char_damage(phantom_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    if Mode == "glacio_chafe":
        # 附加霜渐效应
        title = "洛瑟菈-常态"
        msg = "特定攻击为命中目标附加【霜渐效应】"
        attr.set_env_glacio_chafe()

    # 守岸人buff
    shouanren_buff(attr, 0, 1, isGroup)

    # 仇远buff
    qiuyuan_buff(attr, 0, 1, isGroup)

    return calc_damage_2(attr, role, isGroup, Mode, r)


damage_detail = [
    {
        "title": "追光",
        "func": lambda attr, role: calc_damage_1(attr, role, e="e_spotlight"),
    },
    {
        "title": "历历在目(霜渐)",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "普攻·溯念留形第三段(霜渐)",
        "func": lambda attr, role: calc_damage_2(attr, role, r="a3"),
    },
    {
        "title": "遗忘(三照片-霜渐)",
        "func": lambda attr, role: calc_damage_3(attr, role, photo_count=3),
    },
    {
        "title": "断舍离(霜渐)",
        "func": lambda attr, role: calc_damage_2(attr, role, r="LetItGo"),
    },
    {
        "title": "断舍离(声骸)",
        "func": lambda attr, role: calc_damage_2(attr, role, r="LetItGo", Mode="echo"),
    },
    {
        "title": "01守/01仇/断舍离(声骸)",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
]

rank = damage_detail[4]
