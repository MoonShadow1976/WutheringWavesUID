# 清宵

from ...api.model import RoleDetailData
from ...ascension.char import WavesCharResult, get_char_detail2
from ...damage.damage import DamageAttribute, calc_percent_expression
from ...damage.utils import (
    SkillTreeMap,
    SkillType,
    attack_damage,
    cast_attack,
    cast_damage,
    cast_hit,
    cast_liberation,
    cast_variation,
    hit_damage,
    liberation_damage,
    skill_damage_calc,
)
from .buff import denia_buff, mornye_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    MindlockNum: int = 0,
) -> tuple[str, str]:
    """
    重击·弦剑
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "常态攻击"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "5", skillLevel)
    title = "重击·弦剑"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 常态:清宵技能造成伤害后,为命中目标附加【集谐·偏移】
    title = "清宵-常态"
    msg = "技能造成伤害后附加【集谐·偏移】"
    attr.add_effect(title, msg)
    attr.set_env_tune_strain()

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-识海浩渺"
        msg = "获得1层凝识,造成伤害后为目标附加等同凝识层数的心识锁定"
        if MindlockNum == 0:
            MindlockNum += 1
        attr.add_effect(title, msg)

        title = "固有技能-凝识"
        msg = "施放谐度破坏时将额外附加1层集谐·干涉"
        if chain_num >= 3:
            title = f"{role_name}-二链-固有-凝识"
            msg = "凝识效果附加集谐·干涉层数提升至2层"
        if chain_num >= 3:
            MindlockNum += 3
        else:
            MindlockNum += 2
        attr.add_effect(title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链-回路-天心空明"
        msg = "天心空明效果附加心识锁定层数提升至6层"
        MindlockNum += 6
    else:
        title = "共鸣回路-天心空明"
        msg = "施放重击·弦剑时，对附近的目标附加3层心识锁定"
        MindlockNum += 3
    attr.add_effect(title, msg)

    # 共鸣回路-心识锁定
    MaxMindlockNum = 15
    if chain_num >= 2:
        MaxMindlockNum = 25
        title = f"{role_name}-二链"
        msg = "心识锁定层数上限提升至25"
        attr.add_effect(title, msg)

    MindlockNum = min(MindlockNum, MaxMindlockNum)
    if MindlockNum <= 7:
        Mindlockvalue = (0.02 + 0.05) * MindlockNum
    else:
        Mindlockvalue = 0.05 * 7 + 0.02 * MindlockNum

    if role_breach and role_breach >= 4:
        title = "固有技能-通晓万物,指名破祟"
        msg = f"每层心识伤害提升2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
        attr.add_dmg_bonus(Mindlockvalue, title, msg)

    title = "共鸣回路-心识锁定"
    mag = "对目标附加集谐·干涉后，对目标附加1层心识锁定"
    attr.add_effect(title, mag)
    msg = f"每层心识伤害加深2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
    attr.add_dmg_deepen(Mindlockvalue, title, msg)

    title = "谐度破坏-响应集谐·干涉"
    msg = "清宵于编队中时,目标集谐·干涉层数上限增加1层"
    attr.add_tune_strain_stack(1, title, msg)

    dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
    if chain_num >= 6:
        title2 = f"{role_name}-六链-响应集谐·干涉"
        dmg += " * 120%"
        msg2 = "清宵响应【集谐·干涉】效果提升20%"
        attr.add_effect(title2, msg2)
    msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
    attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 一链:暴击提升16%
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击提升16%"
        attr.add_crit_rate(0.16, title, msg)

    # 二链:重击·弦剑伤害倍率提升40%
    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "重击·弦剑伤害倍率提升40%"
        attr.add_skill_ratio(0.4, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色附加集谐·偏移后，攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 六链:目标受到清宵的重击·弦剑/重击·天钧荡煞·昙体仙身/共鸣解放/巨阙灭迹伤害提升40%
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到清宵的重击·弦剑伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

        title = f"{role_name}-六链-响应集谐·干涉"
        value = (0.0012 * attr.tune_strain_stack * attr.tune_break_boost) * 0.2
        msg = f"清宵响应【集谐·干涉】效果提升20%,当前额外{value * 100:.2f}%"
        attr.add_final_damage(value, title, msg)

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


def calc_damage_2(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    MindlockNum: int = 0,
) -> tuple[str, str]:
    """
    普攻·昙体仙身总伤(4段)
    """
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    title = "普攻·昙体仙身"
    skillParamId = ["24", "25", "26", "27"]
    for i, param_id in enumerate(skillParamId):
        skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], param_id, skillLevel)
        msg = f"技能倍率{skill_multi}"
        attr.add_skill_multi(skill_multi, title + f"第{i + 1}段", msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 常态:清宵技能造成伤害后,为命中目标附加【集谐·偏移】
    title = "清宵-常态"
    msg = "技能造成伤害后附加【集谐·偏移】"
    attr.add_effect(title, msg)
    attr.set_env_tune_strain()

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-识海浩渺"
        msg = "获得1层凝识,造成伤害后为目标附加等同凝识层数的心识锁定"
        if MindlockNum == 0:
            MindlockNum += 1
        attr.add_effect(title, msg)

        title = "固有技能-凝识"
        msg = "施放谐度破坏时将额外附加1层集谐·干涉"
        if chain_num >= 3:
            title = f"{role_name}-二链-固有-凝识"
            msg = "凝识效果附加集谐·干涉层数提升至2层"
        if chain_num >= 3:
            MindlockNum += 3
        else:
            MindlockNum += 2
        attr.add_effect(title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链-回路-天心空明"
        msg = "天心空明效果附加心识锁定层数提升至6层"
        MindlockNum += 6
    else:
        title = "共鸣回路-天心空明"
        msg = "施放重击·弦剑时，对附近的目标附加3层心识锁定"
        MindlockNum += 3
    attr.add_effect(title, msg)

    # 共鸣回路-心识锁定
    MaxMindlockNum = 15
    if chain_num >= 2:
        MaxMindlockNum = 25
        title = f"{role_name}-二链"
        msg = "心识锁定层数上限提升至25"
        attr.add_effect(title, msg)

    MindlockNum = min(MindlockNum, MaxMindlockNum)
    if MindlockNum <= 7:
        Mindlockvalue = (0.02 + 0.05) * MindlockNum
    else:
        Mindlockvalue = 0.05 * 7 + 0.02 * MindlockNum

    if role_breach and role_breach >= 4:
        title = "固有技能-通晓万物,指名破祟"
        msg = f"每层心识伤害提升2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
        attr.add_dmg_bonus(Mindlockvalue, title, msg)

    title = "共鸣回路-心识锁定"
    mag = "对目标附加集谐·干涉后，对目标附加1层心识锁定"
    attr.add_effect(title, mag)
    msg = f"每层心识伤害加深2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
    attr.add_dmg_deepen(Mindlockvalue, title, msg)

    # 谐度破坏-响应集谐·干涉:目标每有一层集谐·干涉,清宵每点谐度破坏增幅使最终伤害提升0.12%
    title = "谐度破坏-响应集谐·干涉"
    msg = "清宵于编队中时,目标集谐·干涉层数上限增加1层"
    attr.add_tune_strain_stack(1, title, msg)

    dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
    if chain_num >= 6:
        title2 = f"{role_name}-六链-响应集谐·干涉"
        dmg += " * 120%"
        msg2 = "清宵响应【集谐·干涉】效果提升20%"
        attr.add_effect(title2, msg2)
    msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
    attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 一链:暴击提升16%
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击提升16%"
        attr.add_crit_rate(0.16, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色附加集谐·偏移后，攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage]
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
    MindlockNum: int = 0,
) -> tuple[str, str]:
    """
    重击·天钧荡煞·昙体仙身(施放重击·弦剑后获得强化)
    """
    # 设置角色伤害类型
    attr.set_char_damage(hit_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣回路"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "29", skillLevel)
    title = "重击·天钧荡煞·昙体仙身"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 常态:清宵技能造成伤害后,为命中目标附加【集谐·偏移】
    title = "清宵-常态"
    msg = "技能造成伤害后附加【集谐·偏移】"
    attr.add_effect(title, msg)
    attr.set_env_tune_strain()

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-识海浩渺"
        msg = "获得1层凝识,造成伤害后为目标附加等同凝识层数的心识锁定"
        if MindlockNum == 0:
            MindlockNum += 1
        attr.add_effect(title, msg)

        title = "固有技能-凝识"
        msg = "施放谐度破坏时将额外附加1层集谐·干涉"
        if chain_num >= 3:
            title = f"{role_name}-二链-固有-凝识"
            msg = "凝识效果附加集谐·干涉层数提升至2层"
        if chain_num >= 3:
            MindlockNum += 3
        else:
            MindlockNum += 2
        attr.add_effect(title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链-回路-天心空明"
        msg = "天心空明效果附加心识锁定层数提升至6层"
        MindlockNum += 6
    else:
        title = "共鸣回路-天心空明"
        msg = "施放重击·弦剑时，对附近的目标附加3层心识锁定"
        MindlockNum += 3
    attr.add_effect(title, msg)

    title = "共鸣回路-天心空明"
    msg = "施放重击·弦剑后,下一次重击·天钧荡煞·昙体仙身伤害倍率提升100%"
    attr.add_skill_ratio_in_skill_description(1, title, msg)

    # 共鸣回路-心识锁定
    MaxMindlockNum = 15
    if chain_num >= 2:
        MaxMindlockNum = 25
        title = f"{role_name}-二链"
        msg = "心识锁定层数上限提升至25"
        attr.add_effect(title, msg)

    MindlockNum = min(MindlockNum, MaxMindlockNum)
    if MindlockNum <= 7:
        Mindlockvalue = (0.02 + 0.05) * MindlockNum
    else:
        Mindlockvalue = 0.05 * 7 + 0.02 * MindlockNum

    if role_breach and role_breach >= 4:
        title = "固有技能-通晓万物,指名破祟"
        msg = f"每层心识伤害提升2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
        attr.add_dmg_bonus(Mindlockvalue, title, msg)

    title = "共鸣回路-心识锁定"
    mag = "对目标附加集谐·干涉后，对目标附加1层心识锁定"
    attr.add_effect(title, mag)
    msg = f"每层心识伤害加深2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
    attr.add_dmg_deepen(Mindlockvalue, title, msg)

    # 谐度破坏-响应集谐·干涉:目标每有一层集谐·干涉,清宵每点谐度破坏增幅使最终伤害提升0.12%
    title = "谐度破坏-响应集谐·干涉"
    msg = "清宵于编队中时,目标集谐·干涉层数上限增加1层"
    attr.add_tune_strain_stack(1, title, msg)

    dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
    if chain_num >= 6:
        title2 = f"{role_name}-六链-响应集谐·干涉"
        dmg += " * 120%"
        msg2 = "清宵响应【集谐·干涉】效果提升20%"
        attr.add_effect(title2, msg2)
    msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
    attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 一链:暴击提升16%
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击提升16%"
        attr.add_crit_rate(0.16, title, msg)

    # 三链-万物和鸣:施放重击·弦剑期间按附近敌人心识锁定最高层数获得,每层使天钧荡煞伤害倍率提升3%
    if chain_num >= 3:
        title = f"{role_name}-三链-万物和鸣"
        value = 0.03 * MindlockNum
        msg = f"每层万物和鸣使伤害倍率提升3%,当前{MindlockNum}层提升{value * 100:.1f}%"
        attr.add_skill_ratio(value, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色附加集谐·偏移后，攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 六链:目标受到清宵的重击·弦剑/重击·天钧荡煞·昙体仙身/共鸣解放/巨阙灭迹伤害提升40%
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到清宵的重击·天钧荡煞·昙体仙身伤害提升40%"
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


def calc_damage_4(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    ExorcisingSealNum: int = 0,
    MindlockNum: int = 0,
) -> tuple[str, str]:
    """
    巨阙灭迹(一链解锁:普攻/空中攻击/普攻·昙体仙身造成伤害后触发)
    """
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    if chain_num < 1:
        return "0", "0"

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 一链:普攻造成伤害后移除清邪剑诀触发巨阙灭迹,造成清宵攻击400%的气动伤害,本次伤害为普攻伤害
    skill_multi = calc_percent_expression("400%")
    title = "巨阙灭迹-倍率"
    msg = "一链:普攻造成伤害后触发巨阙灭迹"
    attr.add_skill_multi(skill_multi, title, msg)

    # 常态:清宵技能造成伤害后,为命中目标附加【集谐·偏移】
    title = "清宵-常态"
    msg = "技能造成伤害后附加【集谐·偏移】"
    attr.add_effect(title, msg)
    attr.set_env_tune_strain()

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-识海浩渺"
        msg = "获得1层凝识,造成伤害后为目标附加等同凝识层数的心识锁定"
        if MindlockNum == 0:
            MindlockNum += 1
        attr.add_effect(title, msg)

        title = "固有技能-凝识"
        msg = "施放谐度破坏时将额外附加1层集谐·干涉"
        if chain_num >= 3:
            title = f"{role_name}-二链-固有-凝识"
            msg = "凝识效果附加集谐·干涉层数提升至2层"
        if chain_num >= 3:
            MindlockNum += 3
        else:
            MindlockNum += 2
        attr.add_effect(title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链-回路-天心空明"
        msg = "天心空明效果附加心识锁定层数提升至6层"
        MindlockNum += 6
    else:
        title = "共鸣回路-天心空明"
        msg = "施放重击·弦剑时，对附近的目标附加3层心识锁定"
        MindlockNum += 3
    attr.add_effect(title, msg)

    # 谐度破坏-响应集谐·干涉:目标每有一层集谐·干涉,清宵每点谐度破坏增幅使最终伤害提升0.12%
    title = "谐度破坏-响应集谐·干涉"
    msg = "清宵于编队中时,目标集谐·干涉层数上限增加1层"
    attr.add_tune_strain_stack(1, title, msg)

    dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
    if chain_num >= 6:
        title2 = f"{role_name}-六链-响应集谐·干涉"
        dmg += " * 120%"
        msg2 = "清宵响应【集谐·干涉】效果提升20%"
        attr.add_effect(title2, msg2)
    msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
    attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 一链:暴击提升16%
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击提升16%"
        attr.add_crit_rate(0.16, title, msg)

        # 巨阙灭迹专属buff(一链解锁,不在共鸣回路心识锁定技能列表内,不叠加基础心识锁定)
        # 一链-清邪剑诀:每移除一层清邪剑诀使目标受到巨阙灭迹伤害提升4%,持续1秒
        ExorcisingSealNum = min(ExorcisingSealNum, 25)
        title = f"{role_name}-一链-清邪剑诀"
        value = 0.04 * ExorcisingSealNum
        msg = f"消耗{ExorcisingSealNum}层清邪剑诀使目标受到巨阙灭迹伤害提升{value * 100:.1f}%"
        attr.add_dmg_bonus(value, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色附加集谐·偏移后，攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    if chain_num >= 6:
        # 六链:目标每拥有1层心识锁定,受到巨阙灭迹伤害加深
        title = f"{role_name}-六链-心识锁定"
        MaxMindlockNum = 25
        MindlockNum = min(MindlockNum, MaxMindlockNum)
        if MindlockNum <= 7:
            value = (0.02 + 0.05) * MindlockNum
        else:
            value = 0.05 * 7 + 0.02 * MindlockNum
        msg = f"每层心识伤害加深2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{value * 100:.1f}%"
        attr.add_dmg_deepen(value, title, msg)

        # 固有技能-通晓万物:巨阙灭迹对拥有心识锁定的目标造成伤害提升
        if role_breach and role_breach >= 4:
            title = f"{role_name}-六链-固有-通晓万物"
            msg = f"对有心识锁定的目标造成伤害提升,每层2%,前7额外5%,当前{value * 100:.1f}%"
            attr.add_dmg_bonus(value, title, msg)

        title = f"{role_name}-六链"
        msg = "目标受到清宵的巨阙灭迹伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage]
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


def calc_damage_5(
    attr: DamageAttribute,
    role: RoleDetailData,
    isGroup: bool = False,
    MindlockNum: int = 0,
) -> tuple[str, str]:
    """
    共鸣解放·天光云影沧澜兴
    """
    # 设置角色伤害类型
    attr.set_char_damage(liberation_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    chain_num = role.get_chain_num()

    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣解放"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)

    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "18", skillLevel)
    title = "共鸣解放·天光云影沧澜兴"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 常态:清宵技能造成伤害后,为命中目标附加【集谐·偏移】
    title = "清宵-常态"
    msg = "技能造成伤害后附加【集谐·偏移】"
    attr.add_effect(title, msg)
    attr.set_env_tune_strain()

    role_breach = role.role.breach
    if role_breach and role_breach >= 2:
        title = "固有技能-识海浩渺"
        msg = "获得1层凝识,造成伤害后为目标附加等同凝识层数的心识锁定"
        if MindlockNum == 0:
            MindlockNum += 1
        attr.add_effect(title, msg)

        title = "固有技能-凝识"
        msg = "施放谐度破坏时将额外附加1层集谐·干涉"
        if chain_num >= 3:
            title = f"{role_name}-二链-固有-凝识"
            msg = "凝识效果附加集谐·干涉层数提升至2层"
        if chain_num >= 3:
            MindlockNum += 3
        else:
            MindlockNum += 2
        attr.add_effect(title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链-回路-天心空明"
        msg = "天心空明效果附加心识锁定层数提升至6层"
        MindlockNum += 6
    else:
        title = "共鸣回路-天心空明"
        msg = "施放重击·弦剑时，对附近的目标附加3层心识锁定"
        MindlockNum += 3
    attr.add_effect(title, msg)

    # 共鸣回路-心识锁定
    MaxMindlockNum = 15
    if chain_num >= 2:
        MaxMindlockNum = 25
        title = f"{role_name}-二链"
        msg = "心识锁定层数上限提升至25"
        attr.add_effect(title, msg)

    MindlockNum = min(MindlockNum, MaxMindlockNum)
    if MindlockNum <= 7:
        Mindlockvalue = (0.02 + 0.05) * MindlockNum
    else:
        Mindlockvalue = 0.05 * 7 + 0.02 * MindlockNum

    if role_breach and role_breach >= 4:
        title = "固有技能-通晓万物,指名破祟"
        msg = f"每层心识伤害提升2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
        attr.add_dmg_bonus(Mindlockvalue, title, msg)

    title = "共鸣回路-心识锁定"
    mag = "对目标附加集谐·干涉后，对目标附加1层心识锁定"
    attr.add_effect(title, mag)
    msg = f"每层心识伤害加深2%,前7层再加5%,上限{(MaxMindlockNum)}层,当前{MindlockNum}层加深{Mindlockvalue * 100:.1f}%"
    attr.add_dmg_deepen(Mindlockvalue, title, msg)

    # 谐度破坏-响应集谐·干涉:目标每有一层集谐·干涉,清宵每点谐度破坏增幅使最终伤害提升0.12%
    title = "谐度破坏-响应集谐·干涉"
    msg = "清宵于编队中时,目标集谐·干涉层数上限增加1层"
    attr.add_tune_strain_stack(1, title, msg)

    dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
    if chain_num >= 6:
        title2 = f"{role_name}-六链-响应集谐·干涉"
        dmg += " * 120%"
        msg2 = "清宵响应【集谐·干涉】效果提升20%"
        attr.add_effect(title2, msg2)
    msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
    attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 一链:暴击提升16%
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "暴击提升16%"
        attr.add_crit_rate(0.16, title, msg)

    # 三链:共鸣解放·天光云影沧澜兴暴击伤害提升100%
    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "共鸣解放·天光云影沧澜兴暴击伤害提升100%"
        attr.add_crit_dmg(1.0, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队伍中的角色附加集谐·偏移后，攻击提升20%"
        attr.add_atk_percent(0.2, title, msg)

    # 六链:目标受到清宵的重击·弦剑/重击·天钧荡煞·昙体仙身/共鸣解放/巨阙灭迹伤害提升40%
    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "目标受到清宵的共鸣解放伤害提升40%"
        attr.add_easy_damage(0.4, title, msg)

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置角色施放技能
    damage_func = [cast_liberation, cast_damage]
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


def calc_damage_10(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    """0+1莫宁/0+1达妮娅/·天钧荡煞·昙体仙身(满心识)"""
    attr.set_char_damage(hit_damage)
    attr.set_char_template("temp_atk")

    title = "清宵-常态"
    msg = "技能造成伤害后附加【集谐·偏移】"
    attr.set_env_tune_strain()

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 达妮娅buff
    denia_buff(attr, 0, 1, isGroup)

    return calc_damage_3(attr, role, isGroup, MindlockNum=30)


def calc_damage_11(attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True) -> tuple[str, str]:
    """0+1莫宁/0+1达妮娅/天光云影沧澜兴(满心识)"""
    attr.set_char_damage(liberation_damage)
    attr.set_char_template("temp_atk")

    title = "清宵-常态"
    msg = "技能造成伤害后附加【集谐·偏移】"
    attr.set_env_tune_strain()

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 达妮娅buff
    denia_buff(attr, 0, 1, isGroup)

    return calc_damage_5(attr, role, isGroup, MindlockNum=30)


# 按输出循环排布:重击·弦剑 -> 普攻·昙体仙身(触发巨阙灭迹) -> 重击·天钧荡煞 -> 巨阙灭迹 -> 共鸣解放
damage_detail = [
    {
        "title": "重击·弦剑",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "普攻·昙体仙身总伤",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "重击·天钧荡煞·昙体仙身",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "天光云影沧澜兴",
        "func": lambda attr, role: calc_damage_5(attr, role),
    },
    {
        "title": "·天钧荡煞·昙体仙身(满心识)",
        "func": lambda attr, role: calc_damage_3(attr, role, MindlockNum=30),
    },
    {
        "title": "天光云影沧澜兴(满心识)",
        "func": lambda attr, role: calc_damage_5(attr, role, MindlockNum=30),
    },
    {
        "title": "巨阙灭迹(满)[1]",
        "func": lambda attr, role: calc_damage_4(attr, role, MindlockNum=30, ExorcisingSealNum=1),
    },
    {
        "title": "巨阙灭迹(满)[25]",
        "func": lambda attr, role: calc_damage_4(attr, role, MindlockNum=30, ExorcisingSealNum=25),
    },
    {
        "title": "01莫/01达/·天钧荡煞·昙体仙身(满)",
        "func": lambda attr, role: calc_damage_10(attr, role),
    },
    {
        "title": "01莫/01达/天光云影沧澜兴(满)",
        "func": lambda attr, role: calc_damage_11(attr, role),
    },
]

# 权重基准:共鸣解放·天光云影沧澜兴(主伤害来源)
rank = damage_detail[2]
