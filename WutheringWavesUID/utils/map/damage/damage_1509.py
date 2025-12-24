# 琳奈

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute, calc_percent_expression
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    attack_damage,
    cast_attack,
    cast_damage,
    cast_liberation,
    liberation_damage,
    skill_damage_calc,
)
from .buff import mornye_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, Interfered: bool = False
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
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "10", skillLevel)
    title = "共鸣解放·爆炸喷涂"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加集谐·偏移 - 光致变染
    title = f"{role_name}-共鸣模态"
    msg = "光致变染为目标附加【集谐·偏移】"
    attr.set_env_tune_strain()
    attr.add_effect(title, msg)

    title = "共鸣回路-视觉冲击"
    msg = "消耗3点【本色】，使附近队伍中所有角色的谐度破坏增幅提升40点"
    attr.add_tune_break_boost(40, title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 3:
        title = "固有技能-《...》"
        msg = "施放变奏时，9秒内自身的衍射伤害加成提升25%"
        attr.add_dmg_bonus(0.25, title, msg)

    title = "共鸣解放"
    msg = "施放时使附近队伍中所有角色的伤害加成提升24%，持续30秒"
    attr.add_dmg_bonus(0.24, title, msg)

    # 设置角色谐度破坏
    if Interfered:
        title = "光谱解析"
        msg = "林奈于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        title = "光谱解析-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "共鸣解放·爆炸喷涂的伤害倍率提升70%"
        attr.add_skill_ratio(0.7, title, msg)

    # 设置角色施放技能 - 增加偏谐值累积效率在前
    damage_func = [cast_attack, cast_damage, cast_liberation]
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
    skill_name: Literal["c1", "c2"] = "c1",
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率
    if skill_name == "c1":
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "9", skillLevel)
        title = "共鸣回路·普攻·视觉冲击"
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)
    else:
        skill_multi_1 = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "20", skillLevel)
        skill_multi_2 = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "21", skillLevel)
        skill_multi_3 = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "22", skillLevel)
        skill_multi = f"{skill_multi_1}+{skill_multi_2}+{skill_multi_3}"
        title = "共鸣回路·普攻·幻光折跃(总倍率)"
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加集谐·偏移 - 光致变染
    title = f"{role_name}-共鸣模态"
    msg = "光致变染为目标附加【集谐·偏移】"
    attr.set_env_tune_strain()
    attr.add_effect(title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage, cast_liberation]
    phase_damage(attr, role, damage_func, isGroup)

    title = "共鸣回路-视觉冲击"
    msg = "消耗3点【本色】，使附近队伍中所有角色的谐度破坏增幅提升40点"
    attr.add_tune_break_boost(40, title, msg)

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 3:
        title = "固有技能-《...》"
        msg = "施放变奏时，9秒内自身的衍射伤害加成提升25%"
        attr.add_dmg_bonus(0.25, title, msg)

    title = "共鸣解放"
    msg = "施放时使附近队伍中所有角色的伤害加成提升24%，持续30秒"
    attr.add_dmg_bonus(0.24, title, msg)

    # 设置角色谐度破坏
    if Interfered:
        title = "光谱解析"
        msg = "林奈于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        title = "光谱解析-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        if skill_name == "c2":
            title = f"{role_name}-一链"
            msg = "普攻·幻光折跃的伤害倍率提升120%"
            attr.add_skill_ratio(1.2, title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)

    if chain_num >= 3:
        if skill_name == "c1":
            title = f"{role_name}-三链"
            msg = "普攻·视觉冲击的伤害倍率提升90%"
            attr.add_skill_ratio(0.9, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 6:
        if skill_name == "c1":
            title = f"{role_name}-六链"
            msg = "3层心之彩使目标受到普攻·视觉冲击的伤害提高30%*3"
            attr.add_easy_damage(0.9, title, msg)

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
    attr.set_char_damage(attack_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    return calc_damage_2(attr, role, isGroup)


def calc_damage_11(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    attr.set_char_damage(attack_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    return calc_damage_2(attr, role, isGroup, Interfered=True)


def calc_damage_12(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    attr.set_char_damage(attack_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 2, 5, isGroup)

    return calc_damage_2(attr, role, isGroup, Interfered=True)


damage_detail = [
    {
        "title": "爆炸喷涂",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "普攻·幻光折跃(总伤)",
        "func": lambda attr, role: calc_damage_2(attr, role, skill_name="c2"),
    },
    {
        "title": "普攻·视觉冲击",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "响应集谐··视觉冲击",
        "func": lambda attr, role: calc_damage_2(attr, role, Interfered=True),
    },
    {
        "title": "0+1莫宁/普攻·视觉冲击",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "0+1莫宁/响应集谐··视觉冲击",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
    {
        "title": "2+5莫宁/响应集谐··视觉冲击",
        "func": lambda attr, role: calc_damage_12(attr, role),
    },
]

rank = damage_detail[2]
