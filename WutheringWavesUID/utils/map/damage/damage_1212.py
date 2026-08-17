# 景燃

from typing import Literal

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute, calc_percent_expression
from ...damage.utils import (
    Shield_Role_Dict,
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
from .buff import iuno_buff, lupa_buff, mornye_buff, motefei_buff, shouanren_buff
from .damage import echo_damage, phase_damage, weapon_damage


def get_shield_count(
    attr: DamageAttribute,
):
    """
    获取队伍中获得护盾的数量
    """
    count = 0
    for char_id in attr.teammate_char_ids:
        if int(char_id) in Shield_Role_Dict.keys():
            count += Shield_Role_Dict[int(char_id)]  # 角色获取的护盾数
    return count


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    skill: Literal["往生送", "黄泉渡"] = "往生送",
) -> tuple[str, str]:
    """
    共鸣技能·往生送/共鸣技能·黄泉渡(抱阳/负阴状态施放,本次伤害为重击伤害)
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    life = attr.effect_life

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    if skill == "往生送":
        skillParamId = "18"
        title = "共鸣技能·往生送"
    else:
        skillParamId = "16"
        title = "共鸣技能·黄泉渡"

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-贴壁听尘"
        msg = "施放变奏/共鸣技能后造成伤害获得护盾"
        attr.add_effect(title, msg)
        attr.set_trigger_shield()

    title = "共鸣回路-幽而复明"
    value = min(0.75, life / 1000 * 0.015)
    msg = f"每1000点生命上限获得1.5%热熔伤害加成,上限75%,当前{value * 100:.1f}%"
    attr.add_dmg_bonus(value, title, msg)

    title = "共鸣回路-阳变阴合"
    value = min(1800, life / 1000 * 36)
    msg = f"每1000点生命上限获得36点攻击,上限1800,当前{value:,.0f}点"
    attr.add_atk_flat(value, title, msg)

    if isGroup:
        title = "变奏技能-祸兮福兮"
        per_layer = min(0.025, life / 1000 * 0.0005)
        shield_count = min(50, 25 + 2 * get_shield_count(attr))
        value = shield_count * per_layer
        msg = f"消耗鬼护转化为祸兮福兮,热熔伤害加成提升最多125%,当前{value * 100:.1f}%"
        attr.add_dmg_bonus(value, title, msg)

    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "共鸣技能伤害倍率提升80%"
        attr.add_skill_ratio(0.8, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色获得护盾时全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到景燃的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_skill, cast_hit, cast_damage]
    if isGroup:
        damage_func.append(cast_variation)
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
) -> tuple[str, str]:
    """
    共鸣解放·万鬼同葬
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    life = attr.effect_life

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "21", skillLevel)
    title = "共鸣解放·万鬼同葬"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-贴壁听尘"
        msg = "施放变奏/共鸣技能后造成伤害获得护盾"
        attr.add_effect(title, msg)
        attr.set_trigger_shield()

    title = "共鸣回路-幽而复明"
    value = min(0.75, life / 1000 * 0.015)
    msg = f"每1000点生命上限获得1.5%热熔伤害加成,上限75%,当前{value * 100:.1f}%"
    attr.add_dmg_bonus(value, title, msg)

    title = "共鸣回路-阳变阴合"
    value = min(1800, life / 1000 * 36)
    msg = f"每1000点生命上限获得36点攻击,上限1800,当前{value:,.0f}点"
    attr.add_atk_flat(value, title, msg)

    if isGroup:
        title = "变奏技能-祸兮福兮"
        per_layer = min(0.025, life / 1000 * 0.0005)
        shield_count = min(50, 25 + 2 * get_shield_count(attr))
        value = shield_count * per_layer
        msg = f"消耗鬼护转化为祸兮福兮,热熔伤害加成提升最多125%,当前{value * 100:.1f}%"
        attr.add_dmg_bonus(value, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色获得护盾时全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到景燃的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_liberation, cast_hit, cast_damage]
    if isGroup:
        damage_func.append(cast_variation)
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
    heavy: Literal["劫魄", "踏罡"] = "劫魄",
) -> tuple[str, str]:
    """
    重击·劫魄/重击·踏罡(荧惑状态消耗命火)
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    life = attr.effect_life

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    if heavy == "劫魄":
        skillParamId = "30"
        hpParamId = "23"
        title = "重击·劫魄"
    else:
        skillParamId = "31"
        hpParamId = "24"
        title = "重击·踏罡"

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    title = "共鸣回路-命火"
    hp_units = min(25, max(0, (life - 25000) / 1000))
    hp_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], hpParamId, skillLevel)
    value = calc_percent_expression(f"({hp_multi})*{hp_units}")
    msg = f"荧惑状态下消耗命火增加重击伤害倍率,当前增加{value * 100:.2f}%"
    if chain_num >= 2:
        # 二链:荧惑状态下命火对重击的倍率增加效果提升46%
        value *= 1.46
        msg += "*146%"
        title2 = f"{role_name}-二链"
        msg2 = "荧惑状态下命火对重击的倍率增加效果提升46%"
        attr.add_effect(title2, msg2)
    attr.add_skill_multi(value, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-贴壁听尘"
        msg = "施放变奏/共鸣技能后造成伤害获得护盾"
        attr.add_effect(title, msg)
        attr.set_trigger_shield()

    title = "共鸣回路-幽而复明"
    value = min(0.75, life / 1000 * 0.015)
    msg = f"每1000点生命上限获得1.5%热熔伤害加成,上限75%,当前{value * 100:.1f}%"
    attr.add_dmg_bonus(value, title, msg)

    if chain_num >= 3:
        title = f"{role_name}-三链-阴阳相生"
        value = min(2500, life / 1000 * 50)
        msg = f"施放共鸣解放后,每1k生命上限获得50攻击,上限2500,当前{value:,.0f}点"
        attr.add_atk_flat(value, title, msg)
    else:
        title = "共鸣回路-阳变阴合"
        value = min(1800, life / 1000 * 36)
        msg = f"每1000点生命上限获得36点攻击,上限1800,当前{value:,.0f}点"
        attr.add_atk_flat(value, title, msg)

    if isGroup:
        title = "变奏技能-祸兮福兮"
        per_layer = min(0.025, life / 1000 * 0.0005)
        shield_count = min(50, 25 + 2 * get_shield_count(attr))
        value = shield_count * per_layer
        msg = f"消耗鬼护转化为祸兮福兮,热熔伤害加成提升最多125%,当前{value * 100:.1f}%"
        attr.add_dmg_bonus(value, title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "重击·劫魄或重击·踏罡伤害倍率提升46%"
        attr.add_skill_ratio(0.46, title, msg)

        title = f"{role_name}-二链-通幽"
        msg = "施放重击·劫魄或重击·踏罡时,造成的伤害加深180%"
        attr.add_dmg_deepen(1.8, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色获得护盾时全属性伤害加成提升20%"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到景燃的重击伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_hit, cast_damage]
    if isGroup:
        damage_func.append(cast_variation)
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


def calc_damage_10(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True):
    attr.set_char_damage(hit_damage)
    attr.set_char_template("temp_atk")

    # 守岸人buff
    shouanren_buff(attr, 0, 1, isGroup)

    # 莫特斐buff
    motefei_buff(attr, 6, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, heavy="踏罡")


def calc_damage_11(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True):
    attr.set_char_damage(hit_damage)
    attr.set_char_template("temp_atk")

    # 守岸人buff
    shouanren_buff(attr, 0, 1, isGroup)

    # 尤诺buff
    iuno_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, heavy="踏罡")


def calc_damage_12(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True):
    attr.set_char_damage(hit_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 露帕buff
    lupa_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, heavy="踏罡")


damage_detail = [
    {
        "title": "共鸣技能·往生送",
        "func": lambda attr, role: calc_damage_1(attr, role, skill="往生送"),
    },
    {
        "title": "共鸣技能·黄泉渡",
        "func": lambda attr, role: calc_damage_1(attr, role, skill="黄泉渡"),
    },
    {
        "title": "共鸣解放·万鬼同葬",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "重击·踏罡",
        "func": lambda attr, role: calc_damage_3(attr, role, heavy="踏罡"),
    },
    {
        "title": "重击·劫魄",
        "func": lambda attr, role: calc_damage_3(attr, role, heavy="劫魄"),
    },
    {
        "title": "01守/61莫/重击·踏罡",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "01莫/01露/重击·踏罡",
        "func": lambda attr, role: calc_damage_12(attr, role),
    },
    {
        "title": "01守/01尤/重击·踏罡",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
]

rank = damage_detail[3]
