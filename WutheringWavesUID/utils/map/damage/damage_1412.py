# 西格莉卡

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    Phantom_Role_Dict,
    SkillTreeMap,
    SkillType,
    cast_damage,
    cast_liberation,
    cast_phantom,
    phantom_damage,
    skill_damage_calc,
)
from .buff import cantarella_buff, qiuyuan_buff, shouanren_buff
from .damage import echo_damage, phase_damage, weapon_damage


def get_phantom_count(
    attr: DamageAttribute,
):
    """
    获取施放声骸技能的次数
    """
    count = len(attr.teammate_char_ids) + 1  # 自己与队友携带的声骸
    for char_id in attr.teammate_char_ids:
        if int(char_id) in Phantom_Role_Dict.keys():
            count += Phantom_Role_Dict[int(char_id)]  # 角色额外释放的声骸技能
    return count


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    actionType: Literal["z", "z1", "z2", "z3", "ez"] = "ez",
    rounds: int = 1,  # 轮数
) -> tuple[str, str]:
    # 设置角色伤害类型
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
    if actionType == "z":
        title = "重击·符语本源"
        type_tree = "24"
    elif actionType == "z1":
        title = "符语爆破"
        type_tree = "25"
    elif actionType == "z2":
        title = "符语链刃"
        type_tree = "26"
    elif actionType == "z3":
        title = "符语日灵"
        type_tree = "27"
    elif actionType == "ez":
        title = "共鸣回路·我即语义"
        type_tree = "28"

    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], type_tree, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色施放技能
    damage_func = [cast_damage, cast_phantom]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 释放声骸技能次数
    phantom_count = get_phantom_count(attr)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        title = "固有技能-语义共鸣-语义的祝福"
        value = 0.03 * phantom_count
        if phantom_count >= 6:
            value += 0.3
        msg = f"每层使气动伤害加成提升3%,6层时额外提升30%,当前{value * 100:.0f}%"
        attr.add_dmg_bonus(value, title, msg)
        msg = f"每层使声骸技能伤害加成提升3%,6层时额外提升30%,当前{value * 100:.0f}%"
        attr.add_dmg_bonus(value, title, msg)

        value = min(0.5, int((attr.energy_regen - 1.25) * 100) * 0.02)
        msg = f"共鸣效率超125%每1%使声骸技能伤害加成提升2%,上限50%,当前{value * 100:.0f}%"
        attr.add_dmg_bonus(value, title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()

    # 设置共鸣回路
    # 「天赋？」可叠加的层数上限为2层，每层可以使得西格莉卡符语爆破、符语链刃、符语日灵和共鸣回路·我即语义伤害加深30%
    innate_gift = 0  # 初始值
    max_innate_gift = 2
    if chain_num >= 3:
        max_innate_gift = 4
        chain_title = f"{role_name}-三链"
        chain_msg = "「天赋？」层数上限改为4层且不再结束该效果"
        attr.add_effect(chain_title, chain_msg)

    # 两种状态计数器
    buff_a_count = 0
    buff_b_count = 0
    while rounds > 0:
        # 附近队伍中所有角色施放声骸技能时，西格莉卡可以获得10点【日灵能量】，上限60点
        soliskin_vitality = min(60, 10 * phantom_count)
        while soliskin_vitality > 0:
            if soliskin_vitality >= 30:
                buff_a_count += 1
                soliskin_vitality -= 30
            else:
                buff_b_count += soliskin_vitality // 10
                soliskin_vitality = 0
        # 三链:「天赋？」层数西格莉卡施放共鸣回路·我即语义后或切换至其他角色时不再结束该效果
        rounds = rounds - 1 if chain_num >= 3 else 0

    if buff_a_count > 0:
        # 若【日灵能量】不少于30点，消耗30点【日灵能量】，本次符语爆破、符语链刃和符语日灵伤害倍率提升50%
        title = "共鸣回路-[日灵能量]大于30点"
        if actionType == "z1" or actionType == "z2" or actionType == "z3":
            value = 0.5 * buff_a_count
            msg = f"消耗30点【日灵能量】伤害倍率提升50%,当前{value * 100:.0f}%"
            attr.add_skill_ratio_in_skill_description(value, title, msg)

        innate_gift = min(max_innate_gift, innate_gift + buff_a_count)
        msg = f"消耗30点【日灵能量】为自身叠加一层「天赋？」,当前{innate_gift}层"
        attr.add_effect(title, msg)
    if buff_b_count > 0:
        # 若【日灵能量】少于30点，消耗全部【日灵能量】，每消耗10点【日灵能量】，使得本次符语爆破、符语链刃和符语日灵造成的伤害加深15%
        title = "共鸣回路-[日灵能量]少于30点"
        if actionType == "z1" or actionType == "z2" or actionType == "z3":
            value = 0.15 * buff_b_count
            msg = f"每消耗10点【日灵能量】伤害加深15%,当前{value * 100:.0f}%"
            attr.add_dmg_deepen(value, title, msg)

    # 设置「天赋？」
    if innate_gift > 0:
        # 每层可以使得西格莉卡符语爆破、符语链刃、符语日灵和共鸣回路·我即语义伤害加深30%
        title = f"{role_name}-共鸣回路-「天赋？」"
        if actionType != "z":
            value = 0.3 * innate_gift
            msg = f"每层使伤害加深30%,当前{value * 100:.0f}%"
            attr.add_dmg_deepen(value, title, msg)
            # 六链：「天赋？」获得下述额外效果：
            # ·每层使得西格莉卡符语爆破、符语链刃、符语日灵和共鸣回路·我即语义造成的伤害加深15%，至多使造成的伤害加深60%。
            # ·每层使得西格莉卡符语爆破、符语链刃、符语日灵和共鸣回路·我即语义造成的伤害无视目标7.5%防御，至多使造成的伤害无视目标30%防御。
            if chain_num >= 6:
                title = f"{role_name}-六链-「天赋？」"
                value = min(0.6, 0.15 * innate_gift)
                msg = f"每层额外使伤害加深15%,至多60%,当前{value * 100:.0f}%"
                attr.add_dmg_deepen(value, title, msg)
                value = min(0.3, 0.075 * innate_gift)
                msg = f"每层额外无视防御7.5%,至多30%,当前{value * 100:.0f}%"
                attr.add_defense_ignore(value, title, msg)

    if chain_num >= 2:
        if actionType == "ez":
            title = f"{role_name}-二链"
            msg = "共鸣回路·我即语义伤害倍率提升120%"
            attr.add_skill_ratio(1.2, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色施放声骸技能时，使队伍中的角色攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到西格莉卡的伤害提升30%"
        attr.add_easy_damage(0.3, title, msg)

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
) -> tuple[str, str]:
    # 设置角色伤害类型
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
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "18", skillLevel)
    title = "如那期望般！"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色施放技能
    damage_func = [cast_liberation, cast_phantom]
    phase_damage(attr, role, damage_func, isGroup)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        title = "固有技能-语义共鸣-语义的祝福"
        phantom_count = get_phantom_count(attr)
        value = 0.03 * phantom_count
        if phantom_count >= 6:
            value += 0.3
        msg = f"每层使气动伤害加成提升3%,6层时额外提升30%,当前{value * 100:.0f}%"
        attr.add_dmg_bonus(value, title, msg)
        msg = f"每层使声骸技能伤害加成提升3%,6层时额外提升30%,当前{value * 100:.0f}%"
        attr.add_dmg_bonus(value, title, msg)

        value = min(0.5, int((attr.energy_regen - 1.25) * 100) * 0.02)
        msg = f"共鸣效率超125%每1%使声骸技能伤害加成提升2%,上限50%,当前{value * 100:.0f}%"
        attr.add_dmg_bonus(value, title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色施放声骸技能时，使队伍中的角色攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "共鸣解放如那期望般！伤害倍率提升30%"
        attr.add_skill_ratio(0.3, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到西格莉卡的伤害提升30%"
        attr.add_easy_damage(0.3, title, msg)

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
    actionType: Literal["z", "z1", "z2", "z3", "ez"] = "ez",
    rounds: int = 1,  # 轮数
) -> tuple[str, str]:
    attr.set_char_damage(phantom_damage)
    attr.set_char_template("temp_atk")

    # 守岸人buff
    shouanren_buff(attr, 0, 1, isGroup)

    # 仇远buff
    qiuyuan_buff(attr, 0, 1, isGroup)

    return calc_damage_1(attr, role, isGroup, actionType, rounds)


def calc_damage_11(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = True,
    actionType: Literal["z", "z1", "z2", "z3", "ez"] = "ez",
    rounds: int = 1,  # 轮数
) -> tuple[str, str]:
    attr.set_char_damage(phantom_damage)
    attr.set_char_template("temp_atk")

    # 守岸人buff
    shouanren_buff(attr, 0, 1, isGroup)

    # 坎特蕾拉buff
    cantarella_buff(attr, 0, 1, isGroup)

    return calc_damage_1(attr, role, isGroup, actionType, rounds)


def calc_damage_12(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    attr.set_char_damage(phantom_damage)
    attr.set_char_template("temp_atk")

    # 守岸人buff
    shouanren_buff(attr, 0, 1, isGroup)

    # 仇远buff
    qiuyuan_buff(attr, 0, 1, isGroup)

    return calc_damage_2(attr, role, isGroup)


damage_detail = [
    {
        "title": "符语日灵",
        "func": lambda attr, role: calc_damage_1(attr, role, actionType="z3"),
    },
    {
        "title": "符语爆破",
        "func": lambda attr, role: calc_damage_1(attr, role, actionType="z1"),
    },
    {
        "title": "如那期望般！",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "回路·我即语义",
        "func": lambda attr, role: calc_damage_1(attr, role, actionType="ez"),
    },
    {
        "title": "01守/坎/(2轮)回路·我即语义",
        "func": lambda attr, role: calc_damage_11(attr, role, actionType="ez", rounds=2),
    },
    {
        "title": "01守/01仇/如那期望般！",
        "func": lambda attr, role: calc_damage_12(attr, role),
    },
    {
        "title": "01守/01仇/回路·我即语义",
        "func": lambda attr, role: calc_damage_10(attr, role, actionType="ez"),
    },
    {
        "title": "01守/01仇/(2轮)回路·我即语义",
        "func": lambda attr, role: calc_damage_10(attr, role, actionType="ez", rounds=2),
    },
]

rank = damage_detail[3]
