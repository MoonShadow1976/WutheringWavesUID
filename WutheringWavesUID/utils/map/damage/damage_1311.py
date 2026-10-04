# 心

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    Electro_Flare_Role_Ids,
    SkillTreeMap,
    SkillType,
    cast_damage,
    cast_skill,
    cast_variation,
    skill_damage,
    skill_damage_calc,
)
from .damage import echo_damage, phase_damage, weapon_damage


def get_electro_num(
    attr: DamageAttribute,
):
    """
    获取电磁人数
    """
    fix_num = 1
    for char_id in attr.teammate_char_ids:
        if int(char_id) in Electro_Flare_Role_Ids:
            fix_num += 1
    return fix_num


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    Mode: Literal["unison", "electro"] = "unison",
) -> tuple[str, str]:
    """
    重击·应世相·镇红尘(应世相阶段,已消耗了尘愿)
    """
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    if Mode == "unison":
        attr.set_teammate_buff()

        if attr.env_unison and (isGroup or attr.group_mode):
            title = "共鸣模态·同奏"
            msg = "拥有响应同奏的能力"
            attr.set_env_unison_response()
            attr.add_effect(title, msg)
    else:
        title = "共鸣模态·电磁"
        msg = "特定攻击为命中目标附加【电磁效应】"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

        attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "52", skillLevel)
    title = "重击·应世相·镇红尘"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    unison_stack = attr.unison_stack
    if Mode == "unison":
        if attr.env_unison_response:
            if role_breach >= 2:
                # 变奏技能·应世相·诸相同奏或变奏技能·照世相·诸相同奏时，自身攻击提升50%
                title = "固有技能-循流引兴替"
                msg = "释放变奏技能时，自身攻击提升50%，持续8秒"
                attr.add_atk_percent(0.5, title, msg)

            # 同奏增益:响应同奏后30秒,每层最终伤害提升3%
            # 自身响应1层+突破4固有1层+六链1层
            attr.add_unison_stack(1, "响应同奏", "获1层同奏增益")
            if role_breach >= 4:
                attr.unison_stack_max += 1
                attr.add_effect("固有技能-信步拾清欢", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, "固有技能-信步拾清欢", "响应同奏时，队伍中的角色获得1层同奏增益")
            if chain_num >= 6:
                attr.unison_stack_max += 1
                attr.add_effect(f"{role_name}-六链", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, f"{role_name}-六链", "响应同奏时，队伍中的角色获得1层同奏增益")
            unison_stack = min(attr.unison_stack, attr.unison_stack_max)
            per_stack = 0.03
            title = "同奏增益"
            value = unison_stack * per_stack
            msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
            attr.add_final_damage(value, title, msg)
    else:
        # 固有技能-循流引兴替(电磁模态):附加电磁效应的角色各提供1层,心自己的转相也算1层,最多2层
        if role_breach >= 2:
            stack = min(2, get_electro_num(attr))
            title = "固有技能-循流引兴替"
            msg = f"队中角色附加电磁效应,导电伤害加成提升{stack * 25}%"
            attr.add_dmg_bonus(0.25 * stack, title, msg)

            # 若漂泊者·导电(1309, 1310)处于同一编队中，则漂泊者施放变奏技能时，心和漂泊者·导电的导电伤害加成提升20%
            for char_id in (1309, 1310):
                if char_id in attr.teammate_char_ids:
                    title = "固有技能-循流引兴替"
                    msg = "漂泊者施放变奏技能后,导电伤害加成提升20%"
                    attr.add_dmg_bonus(0.2, title, msg)
                    break

    # 二链:重击·应世相·步红尘/镇红尘伤害倍率提升60%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "重击·应世相·步红尘/镇红尘伤害倍率提升60%"
        attr.add_skill_ratio(0.6, title, msg)

    # 四链:附加电磁效应或获得/响应同奏后,自身全属性伤害加成提升20%,持续30秒
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "触发后全属性伤害加成提升20%,持续30秒"
        attr.add_dmg_bonus(0.2, title, msg)

    # 六链:目标受到心的共鸣技能伤害提升40%,且共鸣技能伤害无视目标20%防御
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到心的共鸣技能伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)
        msg = "心的共鸣技能伤害无视目标20%防御"
        attr.add_defense_ignore(0.2, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

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


def calc_damage_2(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    Mode: Literal["unison", "electro"] = "electro",
) -> tuple[str, str]:
    """
    共鸣技能·照世相·万阙连衡(照世心满300,进入统御众机)
    """
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    if Mode == "unison":
        attr.set_teammate_buff()

        if attr.env_unison and (isGroup or attr.group_mode):
            title = "共鸣模态·同奏"
            msg = "拥有响应同奏的能力"
            attr.set_env_unison_response()
            attr.add_effect(title, msg)
    else:
        title = "共鸣模态·电磁"
        msg = "特定攻击为命中目标附加【电磁效应】"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

        attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "55", skillLevel)
    title = "共鸣技能·照世相·万阙连衡"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    if Mode == "electro":
        # 固有技能-循流引兴替(电磁模态):附加电磁效应的角色各提供1层,心自己的转相也算1层,最多2层
        if role_breach >= 2:
            stack = min(2, get_electro_num(attr))
            title = "固有技能-循流引兴替"
            msg = f"队中角色附加电磁效应,导电伤害加成提升{stack * 25}%"
            attr.add_dmg_bonus(0.25 * stack, title, msg)

            # 若漂泊者·导电(1309, 1310)处于同一编队中，则漂泊者施放变奏技能时，心和漂泊者·导电的导电伤害加成提升20%
            for char_id in (1309, 1310):
                if char_id in attr.teammate_char_ids:
                    title = "固有技能-循流引兴替"
                    msg = "漂泊者施放变奏技能后,导电伤害加成提升20%"
                    attr.add_dmg_bonus(0.2, title, msg)
                    break

    # 四链:附加电磁效应或获得/响应同奏后,自身全属性伤害加成提升20%,持续30秒
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "触发后全属性伤害加成提升20%,持续30秒"
        attr.add_dmg_bonus(0.2, title, msg)

    # 六链:目标受到心的共鸣技能伤害提升40%,且共鸣技能伤害无视目标20%防御
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到心的共鸣技能伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)
        msg = "心的共鸣技能伤害无视目标20%防御"
        attr.add_defense_ignore(0.2, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

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
    Mode: Literal["unison", "electro"] = "unison",
) -> tuple[str, str]:
    """
    重击·照世相·镇寰宇(统御众机状态内,已消耗承天则)
    """
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    if Mode == "unison":
        attr.set_teammate_buff()

        if attr.env_unison and (isGroup or attr.group_mode):
            title = "共鸣模态·同奏"
            msg = "拥有响应同奏的能力"
            attr.set_env_unison_response()
            attr.add_effect(title, msg)
    else:
        title = "共鸣模态·电磁"
        msg = "特定攻击为命中目标附加【电磁效应】"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

        attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "54", skillLevel)
    title = "重击·照世相·镇寰宇"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    unison_stack = attr.unison_stack
    if Mode == "unison":
        if attr.env_unison_response:
            if role_breach >= 2:
                # 变奏技能·应世相·诸相同奏或变奏技能·照世相·诸相同奏时，自身攻击提升50%
                title = "固有技能-循流引兴替"
                msg = "释放变奏技能时，自身攻击提升50%，持续8秒"
                attr.add_atk_percent(0.5, title, msg)

            # 同奏增益:响应同奏后30秒,每层最终伤害提升3%
            # 自身响应1层+突破4固有1层+六链1层
            attr.add_unison_stack(1, "响应同奏", "获1层同奏增益")
            if role_breach >= 4:
                attr.unison_stack_max += 1
                attr.add_effect("固有技能-信步拾清欢", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, "固有技能-信步拾清欢", "响应同奏时，队伍中的角色获得1层同奏增益")
            if chain_num >= 6:
                attr.unison_stack_max += 1
                attr.add_effect(f"{role_name}-六链", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, f"{role_name}-六链", "响应同奏时，队伍中的角色获得1层同奏增益")
            unison_stack = min(attr.unison_stack, attr.unison_stack_max)
            per_stack = 0.03
            title = "同奏增益"
            value = unison_stack * per_stack
            msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
            attr.add_final_damage(value, title, msg)
    else:
        # 固有技能-循流引兴替(电磁模态):附加电磁效应的角色各提供1层,心自己的转相也算1层,最多2层
        if role_breach >= 2:
            stack = min(2, get_electro_num(attr))
            title = "固有技能-循流引兴替"
            msg = f"队中角色附加电磁效应,导电伤害加成提升{stack * 25}%"
            attr.add_dmg_bonus(0.25 * stack, title, msg)

            # 若漂泊者·导电(1309, 1310)处于同一编队中，则漂泊者施放变奏技能时，心和漂泊者·导电的导电伤害加成提升20%
            for char_id in (1309, 1310):
                if char_id in attr.teammate_char_ids:
                    title = "固有技能-循流引兴替"
                    msg = "漂泊者施放变奏技能后,导电伤害加成提升20%"
                    attr.add_dmg_bonus(0.2, title, msg)
                    break

    # 二链:重击·照世相·临寰宇/镇寰宇伤害倍率提升60%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "重击·照世相·临寰宇/镇寰宇伤害倍率提升60%"
        attr.add_skill_ratio(0.6, title, msg)

    # 四链:附加电磁效应或获得/响应同奏后,自身全属性伤害加成提升20%,持续30秒
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "触发后全属性伤害加成提升20%,持续30秒"
        attr.add_dmg_bonus(0.2, title, msg)

    # 六链:目标受到心的共鸣技能伤害提升40%,且共鸣技能伤害无视目标20%防御
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到心的共鸣技能伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)
        msg = "心的共鸣技能伤害无视目标20%防御"
        attr.add_defense_ignore(0.2, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

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


def calc_damage_4(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    Mode: Literal["unison", "electro"] = "unison",
) -> tuple[str, str]:
    """
    共鸣解放·万阙垂天(退出统御众机后施放)
    """
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    if Mode == "unison":
        attr.set_teammate_buff()

        if attr.env_unison and (isGroup or attr.group_mode):
            title = "共鸣模态·同奏"
            msg = "拥有响应同奏的能力"
            attr.set_env_unison_response()
            attr.add_effect(title, msg)
    else:
        title = "共鸣模态·电磁"
        msg = "特定攻击为命中目标附加【电磁效应】"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

        attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "34", skillLevel)
    title = "共鸣解放·万阙垂天"
    msg = f"倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    unison_stack = attr.unison_stack
    if Mode == "unison":
        if attr.env_unison_response:
            if role_breach >= 2:
                # 变奏技能·应世相·诸相同奏或变奏技能·照世相·诸相同奏时，自身攻击提升50%
                title = "固有技能-循流引兴替"
                msg = "释放变奏技能时，自身攻击提升50%，持续8秒"
                attr.add_atk_percent(0.5, title, msg)

            # 同奏增益:响应同奏后30秒,每层最终伤害提升3%
            # 自身响应1层+突破4固有1层+六链1层
            attr.add_unison_stack(1, "响应同奏", "获1层同奏增益")
            if role_breach >= 4:
                attr.unison_stack_max += 1
                attr.add_effect("固有技能-信步拾清欢", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, "固有技能-信步拾清欢", "响应同奏时，队伍中的角色获得1层同奏增益")
            if chain_num >= 6:
                attr.unison_stack_max += 1
                attr.add_effect(f"{role_name}-六链", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, f"{role_name}-六链", "响应同奏时，队伍中的角色获得1层同奏增益")
            unison_stack = min(attr.unison_stack, attr.unison_stack_max)
            per_stack = 0.03
            title = "同奏增益"
            value = unison_stack * per_stack
            msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
            attr.add_final_damage(value, title, msg)
    else:
        # 固有技能-循流引兴替(电磁模态):附加电磁效应的角色各提供1层,心自己的转相也算1层,最多2层
        if role_breach >= 2:
            stack = min(2, get_electro_num(attr))
            title = "固有技能-循流引兴替"
            msg = f"队中角色附加电磁效应,导电伤害加成提升{stack * 25}%"
            attr.add_dmg_bonus(0.25 * stack, title, msg)

            # 若漂泊者·导电(1309, 1310)处于同一编队中，则漂泊者施放变奏技能时，心和漂泊者·导电的导电伤害加成提升20%
            for char_id in (1309, 1310):
                if char_id in attr.teammate_char_ids:
                    title = "固有技能-循流引兴替"
                    msg = "漂泊者施放变奏技能后,导电伤害加成提升20%"
                    attr.add_dmg_bonus(0.2, title, msg)
                    break

    # 三链:万阙垂天伤害倍率提升70%;同奏模态下暴击伤害提升20%,每层同奏增益额外15%(至多4层)
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "共鸣解放·万阙垂天伤害倍率提升70%"
        attr.add_skill_ratio(0.7, title, msg)
        if Mode == "unison":
            msg = "同奏模态:暴击伤害提升20%"
            attr.add_crit_dmg(0.2, title, msg)
            value = 0.15 * min(unison_stack, 4)
            msg = f"同奏模态:每层同奏增益暴伤额外提升15%,当前{value * 100:.1f}%"
            attr.add_crit_dmg(value, title, msg)

    # 四链:附加电磁效应或获得/响应同奏后,自身全属性伤害加成提升20%,持续30秒
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "触发后全属性伤害加成提升20%,持续30秒"
        attr.add_dmg_bonus(0.2, title, msg)

    # 六链:目标受到心的共鸣技能伤害提升40%,且共鸣技能伤害无视目标20%防御
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到心的共鸣技能伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)
        msg = "心的共鸣技能伤害无视目标20%防御"
        attr.add_defense_ignore(0.2, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

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


def calc_damage_5(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = True,
    Mode: Literal["unison", "electro"] = "unison",
) -> tuple[str, str]:
    """
    变奏技能·照世相·诸相同奏(照世相入场,响应同奏或消耗溯意,仅同奏模态)
    """
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    attr.set_env_unison()
    attr.add_effect("心-同奏模态", "施放共鸣解放·转相时，心获得同奏")

    if Mode == "unison":
        attr.set_teammate_buff()

        if attr.env_unison and (isGroup or attr.group_mode):
            title = "共鸣模态·同奏"
            msg = "拥有响应同奏的能力"
            attr.set_env_unison_response()
            attr.add_effect(title, msg)
    else:
        title = "共鸣模态·电磁"
        msg = "特定攻击为命中目标附加【电磁效应】"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

        attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "变奏技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "46", skillLevel)
    title = "变奏技能·照世相·诸相同奏"
    msg = f"倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    unison_stack = attr.unison_stack
    if Mode == "unison":
        if attr.env_unison_response:
            if role_breach >= 2:
                # 变奏技能·应世相·诸相同奏或变奏技能·照世相·诸相同奏时，自身攻击提升50%
                title = "固有技能-循流引兴替"
                msg = "释放变奏技能时，自身攻击提升50%，持续8秒"
                attr.add_atk_percent(0.5, title, msg)

            # 同奏增益:响应同奏后30秒,每层最终伤害提升3%
            # 自身响应1层+突破4固有1层+六链1层
            attr.add_unison_stack(1, "响应同奏", "获1层同奏增益")
            if role_breach >= 4:
                attr.unison_stack_max += 1
                attr.add_effect("固有技能-信步拾清欢", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, "固有技能-信步拾清欢", "响应同奏时，队伍中的角色获得1层同奏增益")
            if chain_num >= 6:
                attr.unison_stack_max += 1
                attr.add_effect(f"{role_name}-六链", "同奏增益效果的层数上限增加1层")
                attr.add_unison_stack(1, f"{role_name}-六链", "响应同奏时，队伍中的角色获得1层同奏增益")
            unison_stack = min(attr.unison_stack, attr.unison_stack_max)
            per_stack = 0.03
            title = "同奏增益"
            value = unison_stack * per_stack
            msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
            attr.add_final_damage(value, title, msg)
    else:
        # 固有技能-循流引兴替(电磁模态):附加电磁效应的角色各提供1层,心自己的转相也算1层,最多2层
        if role_breach >= 2:
            stack = min(2, get_electro_num(attr))
            title = "固有技能-循流引兴替"
            msg = f"队中角色附加电磁效应,导电伤害加成提升{stack * 25}%"
            attr.add_dmg_bonus(0.25 * stack, title, msg)

            # 若漂泊者·导电(1309, 1310)处于同一编队中，则漂泊者施放变奏技能时，心和漂泊者·导电的导电伤害加成提升20%
            for char_id in (1309, 1310):
                if char_id in attr.teammate_char_ids:
                    title = "固有技能-循流引兴替"
                    msg = "漂泊者施放变奏技能后,导电伤害加成提升20%"
                    attr.add_dmg_bonus(0.2, title, msg)
                    break

    # 一链:诸相同奏变奏伤害倍率提升15%,每层同奏增益额外10%(至多4层)
    if Mode == "unison" and chain_num >= 1:
        title = f"{role_name}-一链"
        value = 0.15 + 0.10 * min(unison_stack, 4)
        msg = f"诸相同奏变奏倍率提升15%,每层同奏增益额外10%,当前{value * 100:.1f}%"
        attr.add_skill_ratio(value, title, msg)

    # 四链:附加电磁效应或获得/响应同奏后,自身全属性伤害加成提升20%,持续30秒
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "触发后全属性伤害加成提升20%,持续30秒"
        attr.add_dmg_bonus(0.2, title, msg)

    # 六链:目标受到心的共鸣技能伤害提升40%,且共鸣技能伤害无视目标20%防御
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到心的共鸣技能伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)
        msg = "心的共鸣技能伤害无视目标20%防御"
        attr.add_defense_ignore(0.2, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill, cast_damage]
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


def calc_damage_10(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    # 设置角色伤害类型
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"

    # 01守岸人/01锁暝(同奏模态)
    attr.set_teammate((1505, 0, 1), (1312, 0, 1))

    return calc_damage_4(attr, role, isGroup)


def calc_damage_11(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    # 设置角色伤害类型
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"

    # 61卜灵/01雷主(电磁模态)
    attr.set_teammate((1307, 6, 1), (1310, 0, 1))

    return calc_damage_4(attr, role, isGroup, Mode="electro")


def calc_damage_12(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    # 设置角色伤害类型
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"

    # 01穗穗/01雷主(电磁模态)
    attr.set_teammate((1110, 0, 1), (1310, 0, 1))

    return calc_damage_4(attr, role, isGroup, Mode="electro")


def calc_damage_13(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    # 设置角色伤害类型
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"

    # 01守岸人/01锁暝(同奏模态入场变奏)
    attr.set_teammate((1505, 0, 1), (1312, 0, 1))

    return calc_damage_5(attr, role, isGroup)


# 按输出流程排布:重击·镇红尘 -> 照世相共鸣技能 -> 重击·镇寰宇 -> 共鸣解放·万阙垂天 -> 照世相变奏入场
# 每种技能各给同奏/电磁两个模态条目,模态在基础函数里用 Mode 切换
damage_detail = [
    {
        "title": "重击·应世相·镇红尘(电磁)",
        "func": lambda attr, role: calc_damage_1(attr, role, Mode="electro"),
    },
    {
        "title": "重击·应世相·镇红尘(同奏)",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "共鸣技能·照世相·万阙连衡(电磁)",
        "func": lambda attr, role: calc_damage_2(attr, role, Mode="electro"),
    },
    {
        "title": "变奏技能·照世相·诸相同奏(同奏)",
        "func": lambda attr, role: calc_damage_5(attr, role),
    },
    {
        "title": "重击·照世相·镇寰宇(电磁)",
        "func": lambda attr, role: calc_damage_3(attr, role, Mode="electro"),
    },
    {
        "title": "重击·照世相·镇寰宇(同奏)",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "共鸣解放·万阙垂天(电磁)",
        "func": lambda attr, role: calc_damage_4(attr, role, Mode="electro"),
    },
    {
        "title": "共鸣解放·万阙垂天(同奏)",
        "func": lambda attr, role: calc_damage_4(attr, role),
    },
    {
        "title": "61卜灵/01雷主/·万阙垂天",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
    {
        "title": "01穗穗/01雷主/·万阙垂天",
        "func": lambda attr, role: calc_damage_12(attr, role),
    },
    {
        "title": "01守/01锁/·照世相·诸相同奏",
        "func": lambda attr, role: calc_damage_13(attr, role),
    },
    {
        "title": "01守/01锁/·万阙垂天",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
]

rank = damage_detail[7]
