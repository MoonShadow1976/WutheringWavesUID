# 莉莉

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    attack_damage,
    cast_attack,
    cast_damage,
    cast_healing,
    cast_hit,
    cast_liberation,
    cast_skill,
    cast_variation,
    heal_bonus,
    hit_damage,
    intro_skill_damage,
    liberation_damage,
    skill_damage,
    skill_damage_calc,
)
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    梦乡治疗量(共鸣解放后每3秒回复一次)
    """
    # 设置角色伤害类型
    attr.set_char_damage(heal_bonus)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "22", skillLevel)
    title = "梦乡治疗量"
    msg = f"技能倍率{skill_multi}"
    attr.add_healing_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 四链:梦乡提供的治疗量提升30%
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "梦乡提供的治疗量提升30%"
        attr.add_dmg_bonus(0.3, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus(needShuxing=False)

    # 设置角色施放技能
    damage_func = [cast_healing]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    healing_bonus = attr.calculate_healing(attr.effect_life)

    crit_damage = f"{healing_bonus:,.0f}"
    return None, crit_damage


def calc_damage_2(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    重击·编织的梦之童话/梦之魇影治疗量(技能期间每秒回复)
    """
    # 设置角色伤害类型
    attr.set_char_damage(heal_bonus)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    _role_name = role.role.roleName
    _chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "12", skillLevel)
    title = "重击治疗量"
    msg = f"技能倍率{skill_multi}"
    attr.add_healing_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 祈梦之愿:每25秒可获得1次,消耗祈梦之愿使本次重击提供的治疗量提升400%
    title = "共鸣回路-祈梦之愿"
    msg = "消耗祈梦之愿,本次重击治疗量提升400%"
    attr.add_skill_ratio_in_skill_description(4.0, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus(needShuxing=False)

    # 设置角色施放技能
    damage_func = [cast_healing]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    healing_bonus = attr.calculate_healing(attr.effect_life)

    crit_damage = f"{healing_bonus:,.0f}"
    return None, crit_damage


def calc_damage_3(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    变奏技能·初绽(变奏入场)
    """
    # 设置角色伤害类型
    attr.set_char_damage(intro_skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    _chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "变奏技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "24", skillLevel)
    title = "变奏技能·初绽"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 设置声骸属性(变奏技能伤害没有对应声骸词条,只吃属性伤害加成)
    attr.set_phantom_dmg_bonus(needPhantom=False)

    # 设置角色施放技能
    damage_func = [cast_variation]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_4(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    共鸣技能·幻梦调和(美梦调和/梦魇调和,两形态倍率相同)
    """
    # 设置角色伤害类型
    attr.set_char_damage(skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    _chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "8", skillLevel)
    title = "共鸣技能·幻梦调和"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

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
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_5(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    重击·编织的梦之童话(绮梦香息满,20段)
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    _chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "14", skillLevel)
    title = "重击·编织的梦之童话"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_hit, cast_damage, cast_healing]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_6(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    重击·梦之童话的落幕(梦铃的祷声满,童话收尾)
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "16", skillLevel)
    title = "重击·梦之童话的落幕"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 落幕:共效超100%时,每1%为该伤害提升0.5%暴击(上限80%)与1%暴击伤害(上限160%)
    if attr.energy_regen > 1:
        title = "梦之童话的落幕"
        dmg = min(0.8, (attr.energy_regen - 1) * 0.5)
        msg = f"共效超100%每1%提升0.5%暴击,当前{dmg * 100:.1f}%"
        attr.add_crit_rate(dmg, title, msg)
        dmg = min(1.6, attr.energy_regen - 1)
        msg = f"共效超100%每1%提升1%暴击伤害,当前{dmg * 100:.1f}%"
        attr.add_crit_dmg(dmg, title, msg)

    # 六链:梦之童话的落幕与梦之魇影的终结造成的衍射伤害额外提升100%
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "落幕/终结造成的衍射伤害额外提升100%"
        attr.add_dmg_bonus(1.0, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_hit, cast_damage, cast_healing]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_7(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    变奏技能·永绽(共鸣解放后替换初绽,六链倍率大幅提升)
    """
    # 设置角色伤害类型
    attr.set_char_damage(intro_skill_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "变奏技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "25", skillLevel)
    title = "变奏技能·永绽"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 永绽:共效超100%时,每1%为该伤害提升0.5%暴击(上限80%)与1%暴击伤害(上限160%)
    if attr.energy_regen > 1:
        title = "变奏技能·永绽"
        dmg = min(0.8, (attr.energy_regen - 1) * 0.5)
        msg = f"共效超100%每1%提升0.5%暴击,当前{dmg * 100:.1f}%"
        attr.add_crit_rate(dmg, title, msg)
        dmg = min(1.6, attr.energy_regen - 1)
        msg = f"共效超100%每1%提升1%暴击伤害,当前{dmg * 100:.1f}%"
        attr.add_crit_dmg(dmg, title, msg)

    # 六链:永绽造成的衍射伤害额外提升700%
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "变奏技能·永绽造成的衍射伤害额外提升700%"
        attr.add_dmg_bonus(7.0, title, msg)

    # 设置声骸属性(变奏技能伤害没有对应声骸词条,只吃属性伤害加成)
    attr.set_phantom_dmg_bonus(needPhantom=False)

    # 设置角色施放技能
    damage_func = [cast_variation]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_8(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    重击·编织的梦之魇影(绮梦香息满,23段)
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    _chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "15", skillLevel)
    title = "重击·编织的梦之魇影"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_hit, cast_damage, cast_healing]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_9(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    重击·梦之魇影的终结(梦铃的祷声满,魇影收尾)
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "17", skillLevel)
    title = "重击·梦之魇影的终结"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 终结:共效超100%时,每1%为该伤害提升0.5%暴击(上限80%)与1%暴击伤害(上限160%)
    if attr.energy_regen > 1:
        title = "梦之魇影的终结"
        dmg = min(0.8, (attr.energy_regen - 1) * 0.5)
        msg = f"共效超100%每1%提升0.5%暴击,当前{dmg * 100:.1f}%"
        attr.add_crit_rate(dmg, title, msg)
        dmg = min(1.6, attr.energy_regen - 1)
        msg = f"共效超100%每1%提升1%暴击伤害,当前{dmg * 100:.1f}%"
        attr.add_crit_dmg(dmg, title, msg)

    # 六链:梦之童话的落幕与梦之魇影的终结造成的衍射伤害额外提升100%
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "落幕/终结造成的衍射伤害额外提升100%"
        attr.add_dmg_bonus(1.0, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_hit, cast_damage, cast_healing]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_10(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    普攻·梦愈净瑕总伤(4段,绮梦香息主要来源)
    """
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    _chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "常态攻击"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    title = "普攻·梦愈净瑕"
    skillParamId = ["1", "2", "3", "4"]
    for i, param_id in enumerate(skillParamId):
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], param_id, skillLevel)
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title + f"第{i + 1}段", msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


def calc_damage_11(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False) -> tuple[str, str]:
    """
    共鸣解放·梦缚持续伤害(梦乡期间单段,此处按一段计;原文未标注伤害类型,按共鸣解放伤害)
    """
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_life")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    _chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "23", skillLevel)
    title = "共鸣解放·梦缚"
    msg = f"单段倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 延奏技能:队伍中的角色全伤害加深25%,持续30秒
    title = f"{role_name}-延奏技能"
    msg = "队伍中的角色全伤害加深25%,持续30秒"
    attr.add_dmg_deepen(0.25, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_liberation, cast_damage]
    phase_damage(attr, role, damage_func, isGroup)

    # 声骸
    echo_damage(attr, isGroup)

    # 武器
    weapon_damage(attr, role.weaponData, damage_func, isGroup)

    # 暴击伤害
    crit_damage = f"{attr.calculate_crit_damage(attr.effect_life):,.0f}"
    # 期望伤害
    expected_damage = f"{attr.calculate_expected_damage(attr.effect_life):,.0f}"
    return crit_damage, expected_damage


# 按输出流程排布:梦乡治疗 -> 重击治疗 -> 变奏初绽 -> 共鸣技能 -> 普攻 -> 重击童话 -> 落幕 -> 解放梦缚 -> 变奏永绽 -> 重击魇影 -> 终结
damage_detail = [
    {
        "title": "梦乡治疗量",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "重击治疗量",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "变奏技能·初绽",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "共鸣技能·幻梦调和",
        "func": lambda attr, role: calc_damage_4(attr, role),
    },
    {
        "title": "普攻·梦愈净瑕总伤",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "重击·编织的梦之童话",
        "func": lambda attr, role: calc_damage_5(attr, role),
    },
    {
        "title": "重击·梦之童话的落幕",
        "func": lambda attr, role: calc_damage_6(attr, role),
    },
    {
        "title": "共鸣解放·梦缚持续伤害",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
    {
        "title": "变奏技能·永绽",
        "func": lambda attr, role: calc_damage_7(attr, role),
    },
    {
        "title": "重击·编织的梦之魇影",
        "func": lambda attr, role: calc_damage_8(attr, role),
    },
    {
        "title": "重击·梦之魇影的终结",
        "func": lambda attr, role: calc_damage_9(attr, role),
    },
]

rank = damage_detail[5]
