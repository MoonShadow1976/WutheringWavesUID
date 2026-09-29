# 锁暝

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    attack_damage,
    cast_attack,
    cast_damage,
    cast_liberation,
    cast_variation,
    liberation_damage,
    skill_damage_calc,
)
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    resonance_intro: bool = False,
) -> tuple[str, str]:
    """
    变奏技能·拢伞形·闪裂/拢伞形·锁妄念·同奏(念起入场)
    """
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "变奏技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    skillParamId = "26" if resonance_intro else "24"
    title = "变奏技能·拢伞形·锁妄念·同奏" if resonance_intro else "变奏技能·拢伞形·闪裂"

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 同奏增益:普通变奏由三链自产1层,响应同奏时另获1层(六链),每层最终伤害提升3%(六链提升至4.5%)
    unison_stack = 0
    if resonance_intro:
        unison_stack = 1 + (1 if chain_num >= 6 else 0)
    elif chain_num >= 3:
        unison_stack = 1
    # 同队心(1311)响应同奏时提供2层,其六链再额外提供1层
    xin_chain = next((m.chain for m in (attr._teammate_config or ()) if m.role_id == 1311), None)
    if xin_chain is not None:
        unison_stack += 2 + (1 if xin_chain >= 6 else 0)
    unison_cap = 2 + (1 if chain_num >= 6 else 0) + (1 if (xin_chain or 0) >= 6 else 0)
    unison_stack = min(unison_stack, unison_cap)
    per_stack = 0.045 if chain_num >= 6 else 0.03
    title = "同奏增益"
    value = unison_stack * per_stack
    msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
    attr.add_final_damage(value, title, msg)

    # 固有技能-雨浸旧契:施放变奏技能后导电伤害加成提升50%,持续15秒
    if role_breach >= 2:
        title = "固有技能-雨浸旧契"
        msg = "变奏后导电伤害加成提升50%,持续15秒"
        attr.add_dmg_bonus(0.5, title, msg)

    # 一链:变奏技能伤害倍率提升60%
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "变奏技能伤害倍率提升60%"
        attr.add_skill_ratio(0.6, title, msg)

    # 二链:暴击伤害提升40%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "暴击伤害提升40%"
        attr.add_crit_dmg(0.4, title, msg)

    # 四链:攻击提升20%
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 响应同奏后30秒内的装备增益窗口(普通变奏不算响应)
    attr.env_unison_response = resonance_intro
    attr.env_unison = False

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_variation, cast_attack, cast_damage]
    if resonance_intro:
        damage_func.append("respond_unison")
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
    resonance_intro: bool = False,
) -> tuple[str, str]:
    """
    变奏技能·解伞形·碎霆/解伞形·旋雷破·同奏(念深入场)
    """
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "变奏技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    skillParamId = "27" if resonance_intro else "25"
    title = "变奏技能·解伞形·旋雷破·同奏" if resonance_intro else "变奏技能·解伞形·碎霆"

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], skillParamId, skillLevel)
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 同奏增益:普通变奏由三链自产1层,响应同奏时另获1层(六链),每层最终伤害提升3%(六链提升至4.5%)
    unison_stack = 0
    if resonance_intro:
        unison_stack = 1 + (1 if chain_num >= 6 else 0)
    elif chain_num >= 3:
        unison_stack = 1
    # 同队心(1311)响应同奏时提供2层,其六链再额外提供1层
    xin_chain = next((m.chain for m in (attr._teammate_config or ()) if m.role_id == 1311), None)
    if xin_chain is not None:
        unison_stack += 2 + (1 if xin_chain >= 6 else 0)
    unison_cap = 2 + (1 if chain_num >= 6 else 0) + (1 if (xin_chain or 0) >= 6 else 0)
    unison_stack = min(unison_stack, unison_cap)
    per_stack = 0.045 if chain_num >= 6 else 0.03
    title = "同奏增益"
    value = unison_stack * per_stack
    msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
    attr.add_final_damage(value, title, msg)

    # 固有技能-雨浸旧契:施放变奏技能后导电伤害加成提升50%,持续15秒
    if role_breach >= 2:
        title = "固有技能-雨浸旧契"
        msg = "变奏后导电伤害加成提升50%,持续15秒"
        attr.add_dmg_bonus(0.5, title, msg)

    # 一链:变奏技能伤害倍率提升60%
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "变奏技能伤害倍率提升60%"
        attr.add_skill_ratio(0.6, title, msg)

    # 二链:暴击伤害提升40%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "暴击伤害提升40%"
        attr.add_crit_dmg(0.4, title, msg)

    # 四链:攻击提升20%
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 响应同奏后30秒内的装备增益窗口(普通变奏不算响应)
    attr.env_unison_response = resonance_intro
    attr.env_unison = False

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_variation, cast_attack, cast_damage]
    if resonance_intro:
        damage_func.append("respond_unison")
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
) -> tuple[str, str]:
    """
    共鸣解放·暝伞形·重锁狱瘴(念深状态,施放后获得同奏)
    """
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
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
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "19", skillLevel)
    title = "共鸣解放·暝伞形·重锁狱瘴"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 同奏增益:普通变奏由三链自产1层,每层最终伤害提升3%(六链提升至4.5%)
    unison_stack = 1 if chain_num >= 3 else 0
    # 同队心(1311)响应同奏时提供2层,其六链再额外提供1层,共同受同奏增益层数上限约束
    xin_chain = next((m.chain for m in (attr._teammate_config or ()) if m.role_id == 1311), None)
    if xin_chain is not None:
        unison_stack += 2 + (1 if xin_chain >= 6 else 0)
    unison_cap = 2 + (1 if chain_num >= 6 else 0) + (1 if (xin_chain or 0) >= 6 else 0)
    unison_stack = min(unison_stack, unison_cap)
    per_stack = 0.045 if chain_num >= 6 else 0.03
    title = "同奏增益"
    value = unison_stack * per_stack
    msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
    attr.add_final_damage(value, title, msg)

    # 二链:暴击伤害提升40%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "暴击伤害提升40%"
        attr.add_crit_dmg(0.4, title, msg)

    # 四链:攻击提升20%
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 五链:共鸣解放·暝伞形·重锁狱瘴伤害倍率提升40%
    if chain_num >= 5:
        title = f"{role_name}-五链"
        msg = "共鸣解放·暝伞形·重锁狱瘴伤害倍率提升40%"
        attr.add_skill_ratio(0.4, title, msg)

    # 解放获得同奏:羁念窗口开启,30秒内不因消耗同奏而结束
    attr.env_unison_response = False
    attr.env_unison = True

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_liberation, cast_damage, "gain_unison", "unison_jinian"]
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
    forbidden_lock: bool = True,
) -> tuple[str, str]:
    """
    普攻·解伞形第四段(破隙消耗同奏进入禁锁契主)
    """
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
    attr.set_teammate_buff()

    role_name = role.role.roleName
    chain_num = role.get_chain_num()
    role_breach = role.role.breach or 0

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "常态攻击"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "7", skillLevel)
    title = "普攻·解伞形第四段"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 同奏增益:普通变奏由三链自产1层,每层最终伤害提升3%(六链提升至4.5%)
    unison_stack = 1 if chain_num >= 3 else 0
    # 同队心(1311)响应同奏时提供2层,其六链再额外提供1层,共同受同奏增益层数上限约束
    xin_chain = next((m.chain for m in (attr._teammate_config or ()) if m.role_id == 1311), None)
    if xin_chain is not None:
        unison_stack += 2 + (1 if xin_chain >= 6 else 0)
    unison_cap = 2 + (1 if chain_num >= 6 else 0) + (1 if (xin_chain or 0) >= 6 else 0)
    unison_stack = min(unison_stack, unison_cap)
    per_stack = 0.045 if chain_num >= 6 else 0.03
    title = "同奏增益"
    value = unison_stack * per_stack
    msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
    attr.add_final_damage(value, title, msg)

    # 二链:暴击伤害提升40%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "暴击伤害提升40%"
        attr.add_crit_dmg(0.4, title, msg)

    # 三链:施放共鸣解放后自身普攻伤害加深30%,持续25秒
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "解放后自身普攻伤害加深30%,持续25秒"
        attr.add_dmg_deepen(0.3, title, msg)

    # 四链:攻击提升20%
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 固有技能-沉契凝锁:禁锁契主使普攻·解伞形倍率提升100%,自身暴击伤害提升100%,持续12秒
    if role_breach >= 4 and forbidden_lock:
        title = "固有技能-沉契凝锁"
        msg = "禁锁契主:普攻·解伞形伤害倍率提升100%"
        attr.add_skill_ratio(1.0, title, msg)
        msg = "禁锁契主:自身暴击伤害提升100%,持续12秒"
        attr.add_crit_dmg(1.0, title, msg)

    # 六链:拥有禁锁契主时暴击伤害额外提升200%
    if chain_num >= 6 and forbidden_lock:
        title = f"{role_name}-六链"
        msg = "禁锁契主期间暴击伤害额外提升200%"
        attr.add_crit_dmg(2.0, title, msg)

    # 破隙消耗同奏与协奏能量:怅念取代羁念,解放在先的30秒窗口仍在
    attr.env_unison_response = False
    attr.env_unison = True

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage, "gain_unison", "consume_concerto"]
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
    isGroup: bool = False,
    forbidden_lock: bool = True,
) -> tuple[str, str]:
    """
    普攻·暝伞形·刻心念(无舍念后施放,一轮点按倍率)
    """
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    # 队友增益默认触发键,配队由配队条目或「换队友」决定
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
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "16", skillLevel)
    title = "普攻·暝伞形·刻心念"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 同奏增益:普通变奏由三链自产1层,每层最终伤害提升3%(六链提升至4.5%)
    unison_stack = 1 if chain_num >= 3 else 0
    # 同队心(1311)响应同奏时提供2层,其六链再额外提供1层,共同受同奏增益层数上限约束
    xin_chain = next((m.chain for m in (attr._teammate_config or ()) if m.role_id == 1311), None)
    if xin_chain is not None:
        unison_stack += 2 + (1 if xin_chain >= 6 else 0)
    unison_cap = 2 + (1 if chain_num >= 6 else 0) + (1 if (xin_chain or 0) >= 6 else 0)
    unison_stack = min(unison_stack, unison_cap)
    per_stack = 0.045 if chain_num >= 6 else 0.03
    title = "同奏增益"
    value = unison_stack * per_stack
    msg = f"当前{unison_stack}层,每层最终伤害提升{per_stack * 100:.1f}%"
    attr.add_final_damage(value, title, msg)

    # 二链:暴击伤害提升40%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "暴击伤害提升40%"
        attr.add_crit_dmg(0.4, title, msg)

    # 三链:施放共鸣解放后自身普攻伤害加深30%,持续25秒
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "解放后自身普攻伤害加深30%,持续25秒"
        attr.add_dmg_deepen(0.3, title, msg)

    # 四链:攻击提升20%
    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 固有技能-沉契凝锁:禁锁契主期间自身暴击伤害提升100%(12秒内)
    if role_breach >= 4 and forbidden_lock:
        title = "固有技能-沉契凝锁"
        msg = "禁锁契主:自身暴击伤害提升100%,持续12秒"
        attr.add_crit_dmg(1.0, title, msg)

    # 六链:刻心念伤害倍率提升50%,禁锁契主期间暴击伤害额外提升200%
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "普攻·暝伞形·刻心念伤害倍率提升50%"
        attr.add_skill_ratio(0.5, title, msg)
        if forbidden_lock:
            msg = "禁锁契主期间暴击伤害额外提升200%"
            attr.add_crit_dmg(2.0, title, msg)

    # 破隙消耗同奏与协奏能量:怅念取代羁念,解放在先的30秒窗口仍在
    attr.env_unison_response = False
    attr.env_unison = True

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage, "gain_unison", "consume_concerto"]
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


def calc_damage_6(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    # 设置角色伤害类型
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"

    # 01守岸人/01散华
    attr.set_teammate((1505, 0, 1), (1102, 0, 1))

    return calc_damage_5(attr, role, isGroup)


def calc_damage_7(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    # 设置角色伤害类型
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"

    # 01守岸人/01心(对比心拐锁暝)
    attr.set_teammate((1505, 0, 1), (1311, 0, 1))

    return calc_damage_5(attr, role, isGroup)


def calc_damage_8(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    # 设置角色伤害类型
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"

    # 01守岸人/61散华
    attr.set_teammate((1505, 0, 1), (1102, 6, 1))

    return calc_damage_5(attr, role, isGroup)


# 按输出流程排布:变奏·闪裂(念起) -> 变奏·碎霆(念深) -> 共鸣解放 -> 普攻·解伞形第四段 -> 刻心念
damage_detail = [
    {
        "title": "变奏技能·拢伞形·闪裂",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "变奏技能·解伞形·碎霆",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "共鸣解放·暝伞形·重锁狱瘴",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "普攻·解伞形第四段",
        "func": lambda attr, role: calc_damage_4(attr, role),
    },
    {
        "title": "普攻·暝伞形·刻心念",
        "func": lambda attr, role: calc_damage_5(attr, role),
    },
    {
        "title": "01守/01心/普攻·暝伞形·刻心念",
        "func": lambda attr, role: calc_damage_7(attr, role),
    },
    {
        "title": "01守/01散/普攻·暝伞形·刻心念",
        "func": lambda attr, role: calc_damage_6(attr, role),
    },
    {
        "title": "01守/61散/普攻·暝伞形·刻心念",
        "func": lambda attr, role: calc_damage_8(attr, role),
    },
]

rank = damage_detail[4]
