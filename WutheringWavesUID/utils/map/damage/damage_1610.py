# 秧秧·玄翎

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    Abnormal_Level_Dict,
    SkillTreeMap,
    SkillType,
    cast_damage,
    cast_hit,
    cast_liberation,
    cast_skill,
    cast_variation,
    hit_damage,
    skill_damage_calc,
)
from .buff import chisa_buff, motefei_buff, suisui_buff
from .damage import echo_damage, phase_damage, weapon_damage


def get_havoc_bane_level(
    attr: DamageAttribute,
):
    """
    获取虚湮效应层数上限
    """
    count = 3  # 初始3
    for char_id in attr.teammate_char_ids:
        if int(char_id) in Abnormal_Level_Dict.keys():
            count += Abnormal_Level_Dict[int(char_id)]  # 角色额外增加的层数
    return count


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

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    title = "裁羽寂万音"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "1", skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    title = "秧秧·玄翎-常态"
    msg = "特定攻击为命中目标附加【虚湮效应】"
    attr.set_env_havoc_bane()
    attr.add_effect(title, msg)

    level = get_havoc_bane_level(attr)

    chain_num = role.get_chain_num()
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "一定范围内的目标【虚湮效应】层数上限增加3层"
        level += 3
        attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        if level >= 3:
            title = "固有技能-恒守之誓"
            msg = "3层【虚湮效应】使秧秧·玄翎对其造成的伤害加深30%"
            attr.add_dmg_deepen(0.3, title, msg)

        if level >= 6:
            title = "固有技能-恒守之誓"
            msg = "6层【虚湮效应】使秧秧·玄翎对其造成的伤害加深36%"
            attr.add_dmg_deepen(0.36, title, msg)

    # # 共鸣回路
    # title = "共鸣回路-羽誓"
    # msg = "6层羽誓使特定攻击暴击伤害提升150%"
    # attr.add_crit_dmg(1.5, title, msg)

    # 设置角色buff

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "共鸣解放裁羽寂万音造成的伤害加深175%"
        attr.add_dmg_deepen(1.75, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "万声皆流:目标受到秧秧·玄翎的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill, cast_hit, cast_damage, cast_liberation]
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
    FC: Literal["HitAzure", "HavocinBloomStage"] = "HitAzure",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    if FC == "HitAzure":
        title = "重击·苍剑式"
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "3", skillLevel)
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)
    elif FC == "HavocinBloomStage":
        title = "湮象风华"
        skillParamId = ["6", "7", "8"]
        for i, skill in enumerate(skillParamId):
            skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skill, skillLevel)
            msg = f"技能倍率{skill_multi}"
            attr.add_skill_multi(skill_multi, title + f"第{i + 1}段", msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    title = "秧秧·玄翎-常态"
    msg = "特定攻击为命中目标附加【虚湮效应】"
    attr.set_env_havoc_bane()
    attr.add_effect(title, msg)

    level = get_havoc_bane_level(attr)

    chain_num = role.get_chain_num()
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "一定范围内的目标【虚湮效应】层数上限增加3层"
        level += 3
        attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        if level >= 3:
            title = "固有技能-恒守之誓"
            msg = "3层【虚湮效应】使秧秧·玄翎对其造成的伤害加深30%"
            attr.add_dmg_deepen(0.3, title, msg)

        if level >= 6:
            title = "固有技能-恒守之誓"
            msg = "6层【虚湮效应】使秧秧·玄翎对其造成的伤害加深36%"
            attr.add_dmg_deepen(0.36, title, msg)

    # 共鸣回路
    title = "共鸣回路-羽誓"
    msg = "6层羽誓使特定攻击暴击伤害提升150%"
    attr.add_crit_dmg(1.5, title, msg)

    title = "共鸣回路-苍翎"
    msg = "暴击伤害提升160%"
    attr.add_crit_dmg(1.6, title, msg)

    # 设置角色buff

    # 设置角色buff

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "造成的伤害提升100%"
        attr.add_dmg_bonus(1, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "万声皆流:目标受到秧秧·玄翎的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill, cast_hit, cast_damage, cast_liberation]
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
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True, d: Literal["r", "a"] = "r"
) -> tuple[str, str]:
    attr.set_char_damage(hit_damage)
    attr.set_char_template("temp_atk")

    title = "秧秧·玄翎-常态"
    msg = "特定攻击为命中目标附加【虚湮效应】"
    attr.set_env_havoc_bane()

    # 穗穗buff
    suisui_buff(attr, 0, 1, isGroup)

    # 莫特斐buff
    motefei_buff(attr, 6, 5, isGroup)

    if d == "r":
        return calc_damage_1(attr, role, isGroup)
    else:
        return calc_damage_2(attr, role, isGroup, FC="HavocinBloomStage")


def calc_damage_11(
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True, d: Literal["r", "a"] = "r"
) -> tuple[str, str]:
    attr.set_char_damage(hit_damage)
    attr.set_char_template("temp_atk")

    title = "秧秧·玄翎-常态"
    msg = "特定攻击为命中目标附加【虚湮效应】"
    attr.set_env_havoc_bane()

    # 穗穗buff
    suisui_buff(attr, 0, 1, isGroup)

    # 千咲buff
    chisa_buff(attr, 0, 1, isGroup)

    if d == "r":
        return calc_damage_1(attr, role, isGroup)
    else:
        return calc_damage_2(attr, role, isGroup, FC="HavocinBloomStage")


damage_detail = [
    {
        "title": "裁羽寂万音",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "重击·苍剑式",
        "func": lambda attr, role: calc_damage_2(attr, role, FC="HitAzure"),
    },
    {
        "title": "湮象风华总伤",
        "func": lambda attr, role: calc_damage_2(attr, role, FC="HavocinBloomStage"),
    },
    {
        "title": "01穗/65莫/裁羽寂万音",
        "func": lambda attr, role: calc_damage_10(attr, role, d="r"),
    },
    {
        "title": "01穗/65莫/湮象风华总伤",
        "func": lambda attr, role: calc_damage_10(attr, role, d="a"),
    },
    {
        "title": "01穗/01千/裁羽寂万音",
        "func": lambda attr, role: calc_damage_11(attr, role, d="r"),
    },
    {
        "title": "01穗/01千/湮象风华总伤",
        "func": lambda attr, role: calc_damage_11(attr, role, d="a"),
    },
]

rank = damage_detail[0]
