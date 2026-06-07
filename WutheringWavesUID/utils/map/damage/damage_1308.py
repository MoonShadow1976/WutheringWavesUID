# 丽贝卡

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
    cast_variation,
    skill_damage_calc,
)
from .buff import lucy_buff, mornye_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    r: Literal["r_1", "r_2", "r_3", "r_sum", "r_end"] = "r_end",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    if r == "r_sum":
        title = "【32型重机枪】总伤"
        # 取提升2次的倍率
        skill_multi_base = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "3", skillLevel)
        skill_multi = f"{skill_multi_base}*{90 / 6}"  # 【过载】上限为90点，每次6点
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)
    else:
        if r == "r_1":
            title = "【31型重机枪】"
            skillParamId = "1"
        elif r == "r_2":
            title = "【32型重机枪】威力提升1次"
            skillParamId = "2"
        elif r == "r_3":
            title = "【32型重机枪】威力提升2次"
            skillParamId = "3"
        elif r == "r_end":
            title = "大烟花！"
            skillParamId = "4"
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加骇破·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()
    attr.add_effect(title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能·该你了！"
        msg = "攻击提升10%*2"
        attr.add_atk_percent(0.2, title, msg)
        msg = "附加【骇破·偏移】时，谐度破坏增幅提升30点"
        attr.add_tune_break_boost(30, title, msg)

    if role_breach and role_breach >= 4:
        title = "固有技能·有破绽！"
        msg = "施放共鸣解放·狂欢时间！时，角色攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 共鸣回路
    title = "共鸣回路-小孩子才做选择！"
    msg = "同时获得【猎手】和【铁胆】模式的属性加成效果"
    attr.add_effect(title, msg)

    title = "猎手模式"
    msg = "丽贝卡暴击伤害提升30%"
    attr.add_crit_dmg(0.3, title, msg)

    title = "铁胆模式"
    msg = "丽贝卡造成伤害无视目标15%防御"
    attr.add_defense_ignore(0.15, title, msg)

    # 设置角色谐度破坏

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "队伍中的角色全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)
        msg = "附加【骇破·偏移】时，全伤害加深15%"
        attr.add_dmg_deepen(0.15, title, msg)

    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "共鸣解放伤害倍率提升60%"
        attr.add_skill_ratio(0.6, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "小孩子才做选择！属性加成效果额外提升60%"
        attr.add_effect(title, msg)

        title = f"{role_name}-四链-猎手模式"
        msg = "丽贝卡暴击伤害提升18%"
        attr.add_crit_dmg(0.18, title, msg)

        title = f"{role_name}-四链-铁胆模式"
        msg = "丽贝卡造成伤害无视目标9%防御"
        attr.add_defense_ignore(0.09, title, msg)

    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "附加【骇破·偏移】时，普攻伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    # 设置角色施放技能
    damage_func = [cast_variation, cast_skill, cast_damage, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    if chain_num >= 6:
        title = f"{role_name}-六链"  # 暂时无法细分加成区(属性加成、技能加成、单独加成)
        dmg = attr.dmg_bonus * 0.4
        msg = f"所有获得的普攻伤害加成数值提升40%,当前提升{dmg * 100:,.1f}%"
        attr.add_dmg_bonus(dmg, title, msg)
        attr.add_effect("!注意!", "暂时无法细分加成区, 故六链具体提升比实际效果高")

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
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    title = "丽贝卡-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()

    # 莫宁Buff
    mornye_buff(attr, 1, 1, isGroup)

    # 露西buff
    lucy_buff(attr, 0, 1, isGroup)

    return calc_damage_1(attr, role, isGroup, r="r_sum")


def calc_damage_11(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = True,
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    title = "丽贝卡-常态"
    msg = "特定攻击为命中目标附加【骇破·偏移】"
    attr.set_env_hack()

    # 莫宁Buff
    mornye_buff(attr, 1, 1, isGroup)

    # 露西buff
    lucy_buff(attr, 0, 1, isGroup)

    return calc_damage_1(attr, role, isGroup, r="r_end")


damage_detail = [
    {
        "title": "31型重机枪",
        "func": lambda attr, role: calc_damage_1(attr, role, r="r_1"),
    },
    {
        "title": "31型重机枪(提升2次)",
        "func": lambda attr, role: calc_damage_1(attr, role, r="r_3"),
    },
    {
        "title": "31型重机枪-总伤",
        "func": lambda attr, role: calc_damage_1(attr, role, r="r_sum"),
    },
    {
        "title": "大烟花！",
        "func": lambda attr, role: calc_damage_1(attr, role, r="r_end"),
    },
    {
        "title": "11莫/01露/31型重机枪-总伤",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "11莫/01露/大烟花！",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
]

rank = damage_detail[3]
