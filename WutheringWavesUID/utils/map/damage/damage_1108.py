# 绯雪

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    Glacio_Chafe_Role_Ids,
    Havoc_Bane_Role_Ids,
    SkillTreeMap,
    SkillType,
    cast_liberation,
    liberation_damage,
    skill_damage_calc,
)
from .buff import chisa_buff, lynae_buff
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
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, z: Literal["z1", "z2"] = "z1"
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "常态攻击"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率
    skillParamId = "105" if z == "z1" else "114"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    title = "重击·寒簇·常世身" if z == "z1" else "重击·枯霜·预求身"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    title = "常态"
    msg = "特定攻击为命中目标附加【霜渐效应】"
    attr.set_env_glacio_chafe()
    attr.add_effect(title, msg)

    # 设置角色施放技能
    damage_func = [cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach is not None and role_breach >= 2:
        role_num = get_role_num(attr, Glacio_Chafe_Role_Ids + Havoc_Bane_Role_Ids)
        # 1层【雪锈】：自身为队伍中登场角色时，一定范围内的目标受到【霜冻效应】伤害加深30%。绯雪的暴击伤害提升40%。
        if role_num >= 1:
            title = f"{role_num}层雪锈-一"
            if attr.env_glacio_chafe_deepen:
                msg = "目标受到【霜冻效应】伤害加深30%"
                attr.add_dmg_deepen(0.3, title, msg)
            msg = "绯雪的暴击伤害提升40%"
            attr.add_crit_dmg(0.4, title, msg)
        # 2层【雪锈】：自身为队伍中登场角色时，每次自身附加【霜渐效应】时，额外附加一段102%异常倍率的【霜冻效应】伤害。
        if role_num >= 2:
            title = f"{role_num}层雪锈-二"
            if chain_num >= 6:
                msg = "绯雪的暴击伤害提升40%"
                attr.add_crit_dmg(0.4, title + "-六链", msg)
        # 3层【雪锈】：自身为队伍中登场角色时，一定范围内的目标受到【霜冻效应】伤害额外加深30%。
        if role_num >= 3:
            title = f"{role_num}层雪锈-三"
            if attr.env_glacio_chafe_deepen:
                msg = "目标受到【霜冻效应】伤害额外加深30%。"
                attr.add_dmg_deepen(0.3, title, msg)
                if chain_num >= 6:
                    msg = "目标受到【霜冻效应】的最终伤害提升25%"
                    attr.add_final_damage(0.25, title + "-六链", msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "重击·寒簇·常世身和重击·枯霜·预求身的伤害倍率提升160%。"
        attr.add_skill_ratio(1.6, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "施放共鸣技能后，造成的伤害提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage():,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage():,.0f}"
    return crit_damage, expected_damage


def calc_damage_2(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
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
    skillParamId = "28"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    title = "普攻·居合"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    title = "常态"
    msg = "特定攻击为命中目标附加【霜渐效应】"
    attr.set_env_glacio_chafe()
    attr.add_effect(title, msg)

    # 设置角色施放技能
    damage_func = [cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach is not None and role_breach >= 2:
        role_num = get_role_num(attr, Glacio_Chafe_Role_Ids + Havoc_Bane_Role_Ids)
        # 1层【雪锈】：自身为队伍中登场角色时，一定范围内的目标受到【霜冻效应】伤害加深30%。绯雪的暴击伤害提升40%。
        if role_num >= 1:
            title = f"{role_num}层雪锈-一"
            if attr.env_glacio_chafe_deepen:
                msg = "目标受到【霜冻效应】伤害加深30%"
                attr.add_dmg_deepen(0.3, title, msg)
            msg = "绯雪的暴击伤害提升40%"
            attr.add_crit_dmg(0.4, title, msg)
        # 2层【雪锈】：自身为队伍中登场角色时，每次自身附加【霜渐效应】时，额外附加一段102%异常倍率的【霜冻效应】伤害。
        if role_num >= 2:
            title = "{role_name}层雪锈-二"
            if chain_num >= 6:
                msg = "绯雪的暴击伤害提升40%"
                attr.add_crit_dmg(0.4, title + "-六链", msg)
        # 3层【雪锈】：自身为队伍中登场角色时，一定范围内的目标受到【霜冻效应】伤害额外加深30%。
        if role_num >= 3:
            title = f"{role_num}层雪锈-三"
            if attr.env_glacio_chafe_deepen:
                msg = "目标受到【霜冻效应】伤害额外加深30%。"
                attr.add_dmg_deepen(0.3, title, msg)
                if chain_num >= 6:
                    msg = "目标受到【霜冻效应】的最终伤害提升25%"
                    attr.add_final_damage(0.25, title + "-六链", msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "普攻·居合的伤害倍率提升125%"
        attr.add_skill_ratio(1.25, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "施放共鸣技能后，造成的伤害提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

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
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, r: Literal["r1", "r2"] = "r1", p_num: int = 1
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
    skillParamId = "22" if r == "r1" else "23"
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    title = "预求我身·见心" if r == "r1" else "预求我身·归刃"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    if r == "r2":
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "24", skillLevel)
        skill_multi = f"{p_num} * {skill_multi}"
        title = "【锻雪·归刃】增加倍率"
        msg = f"增加技能倍率 {skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    title = "常态"
    msg = "特定攻击为命中目标附加【霜渐效应】"
    attr.set_env_glacio_chafe()
    attr.add_effect(title, msg)

    # 设置角色施放技能
    damage_func = [cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach is not None and role_breach >= 2:
        role_num = get_role_num(attr, Glacio_Chafe_Role_Ids + Havoc_Bane_Role_Ids)
        # 1层【雪锈】：自身为队伍中登场角色时，一定范围内的目标受到【霜冻效应】伤害加深30%。绯雪的暴击伤害提升40%。
        if role_num >= 1:
            title = f"{role_num}层雪锈-一"
            if attr.env_glacio_chafe_deepen:
                msg = "目标受到【霜冻效应】伤害加深30%"
                attr.add_dmg_deepen(0.3, title, msg)
            msg = "绯雪的暴击伤害提升40%"
            attr.add_crit_dmg(0.4, title, msg)
        # 2层【雪锈】：自身为队伍中登场角色时，每次自身附加【霜渐效应】时，额外附加一段102%异常倍率的【霜冻效应】伤害。
        if role_num >= 2:
            title = f"{role_num}层雪锈-二"
            if chain_num >= 6:
                msg = "绯雪的暴击伤害提升40%"
                attr.add_crit_dmg(0.4, title + "-六链", msg)
        # 3层【雪锈】：自身为队伍中登场角色时，一定范围内的目标受到【霜冻效应】伤害额外加深30%。
        if role_num >= 3:
            title = f"{role_num}层雪锈-三"
            if attr.env_glacio_chafe_deepen:
                msg = "目标受到【霜冻效应】伤害额外加深30%。"
                attr.add_dmg_deepen(0.3, title, msg)
                if chain_num >= 6:
                    msg = "目标受到【霜冻效应】的最终伤害提升25%"
                    attr.add_final_damage(0.25, title + "-六链", msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "施放共鸣技能后，造成的伤害提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "预求我身·见心、预求我身·归刃暴击伤害提升500%"
        attr.add_crit_dmg(5, title, msg)

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
    """0+1千咲/0+1琳奈/归刃伤害"""
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_atk")

    # 千咲buff
    chisa_buff(attr, 0, 1, isGroup)

    # 琳奈buff
    lynae_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, r="r2", p_num=1)


damage_detail = [
    {
        "title": "重击·寒簇·常世身",
        "func": lambda attr, role: calc_damage_1(attr, role, z="z1"),
    },
    {
        "title": "预求我身·见心",
        "func": lambda attr, role: calc_damage_3(attr, role, r="r1"),
    },
    {
        "title": "普攻·居合",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "重击·枯霜·预求身",
        "func": lambda attr, role: calc_damage_1(attr, role, z="z2"),
    },
    {
        "title": "预求我身·归刃(一锻雪)",
        "func": lambda attr, role: calc_damage_3(attr, role, r="r2", p_num=1),
    },
    {
        "title": "预求我身·归刃(三锻雪)",
        "func": lambda attr, role: calc_damage_3(attr, role, r="r2", p_num=3),
    },
    {
        "title": "01咲/01琳/·归刃(一锻雪)",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
]

rank = damage_detail[4]
