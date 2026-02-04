# 陆·赫斯

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
    cast_skill,
    skill_damage_calc,
)
from .buff import lynae_buff, mornye_buff
from .damage import echo_damage, phase_damage, weapon_damage


def calc_damage_1(
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, Interfered: bool = False
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "20", skillLevel)
    title = "普攻·流金贯行"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加集谐·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【集谐·偏移】"
    attr.set_env_tune_strain()
    attr.add_effect(title, msg)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        if attr.env_tune_strain:
            title = "固有技能-无因的医谕"
            max_deepen = 0.3
            deepen_per_TBB = 0.05

            if chain_num >= 2:
                title = "固有技能-二链-无因的医谕"
                max_deepen = 0.6
                deepen_per_TBB = 0.1

            deepen = min(max_deepen, (attr.tune_break_boost // 10) * deepen_per_TBB)
            msg = f"每10点谐度破坏增幅使伤害加深{deepen_per_TBB * 100:.0f}%，最高{max_deepen * 100:.0f}%。当前提升{deepen * 100:.2f}%"
            attr.add_dmg_deepen(deepen, title, msg)

        title = "固有技能-无因的医谕"
        msg = "附加集谐·偏移或造成谐度破坏伤害后，陆·赫斯攻击提升25%"
        attr.add_atk_percent(0.25, title, msg)

    # 设置角色谐度破坏
    if Interfered:
        title = "一场关于光的默辩"
        msg = "陆·赫斯在编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        if chain_num >= 6:
            title = f"{role_name}-六链"
            msg = "将目标当前的集谐·干涉提升2层，且此效果无视层数上限"
            attr.add_tune_strain_stack(2, title, msg)

        title = "一场关于光的默辩-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "空中攻击伤害加成提升150%"
        attr.add_dmg_bonus(1.5, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队中角色造成谐度破坏伤害后使队中所有角色伤害提升20%，无法叠加"
        attr.add_dmg_bonus(0.2, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage]
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
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, Interfered: bool = False
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    # 设置角色模板  "temp_atk", "temp_life", "temp_def"
    attr.set_char_template("temp_atk")

    role_name = role.role.roleName
    # 获取角色详情
    char_result: WavesCharResult = get_char_detail2(role)

    skill_type: SkillType = "共鸣技能"
    # 获取角色技能等级
    skillLevel = role.get_skill_level(skill_type)
    # 技能技能倍率
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "19", skillLevel)
    title = "斩杀日冕·曜"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加集谐·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【集谐·偏移】"
    attr.set_env_tune_strain()
    attr.add_effect(title, msg)

    title = "共鸣回路-黄金的裁量"
    msg = "所有形态的共鸣技能斩杀日冕伤害倍率提升110%"
    attr.add_skill_ratio_in_skill_description(1.1, title, msg)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        if attr.env_tune_strain:
            title = "固有技能-无因的医谕"
            max_deepen = 0.3
            deepen_per_TBB = 0.05

            if chain_num >= 2:
                title = "固有技能-二链-无因的医谕"
                max_deepen = 0.6
                deepen_per_TBB = 0.1

            deepen = min(max_deepen, (attr.tune_break_boost // 10) * deepen_per_TBB)
            msg = f"每10点谐度破坏增幅使伤害加深{deepen_per_TBB * 100:.0f}%，最高{max_deepen * 100:.0f}%。当前提升{deepen * 100:.2f}%"
            attr.add_dmg_deepen(deepen, title, msg)

        title = "固有技能-无因的医谕"
        msg = "附加集谐·偏移或造成谐度破坏伤害后，陆·赫斯攻击提升25%"
        attr.add_atk_percent(0.25, title, msg)

    # 设置角色谐度破坏
    if Interfered:
        title = "一场关于光的默辩"
        msg = "陆·赫斯在编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        if chain_num >= 6:
            title = f"{role_name}-六链"
            msg = "将目标当前的集谐·干涉提升2层，且此效果无视层数上限"
            attr.add_tune_strain_stack(2, title, msg)

        title = "一场关于光的默辩-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "空中攻击伤害加成提升150%"
        attr.add_dmg_bonus(1.5, title, msg)

    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "黄金的裁量状态下斩杀日冕伤害倍率提升136%"
        attr.add_skill_ratio_in_skill_description(1.36, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队中角色造成谐度破坏伤害后使队中所有角色伤害提升20%，无法叠加"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "队中角色造成谐度破坏伤害时使陆·赫斯斩杀日冕的伤害提升30%"
        attr.add_dmg_bonus(0.3, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_skill, cast_damage]
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
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, Interfered: bool = False
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
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "1", skillLevel)
    title = "判决大地裂响"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 设置角色等级
    attr.set_character_level(role.role.level)

    # 附加集谐·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【集谐·偏移】"
    attr.set_env_tune_strain()
    attr.add_effect(title, msg)

    title = "共鸣回路-黄金的裁量"
    msg = "释放斩杀日冕·曜后空中攻击·判决大地裂响伤害倍率提升110%"
    attr.add_skill_ratio_in_skill_description(1.1, title, msg)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        if attr.env_tune_strain:
            title = "固有技能-无因的医谕"
            max_deepen = 0.3
            deepen_per_TBB = 0.05

            if chain_num >= 2:
                title = "固有技能-二链-无因的医谕"
                max_deepen = 0.6
                deepen_per_TBB = 0.1

            deepen = min(max_deepen, (attr.tune_break_boost // 10) * deepen_per_TBB)
            msg = f"每10点谐度破坏增幅使伤害加深{deepen_per_TBB * 100:.0f}%，最高{max_deepen * 100:.0f}%。当前提升{deepen * 100:.2f}%"
            attr.add_dmg_deepen(deepen, title, msg)

        title = "固有技能-无因的医谕"
        msg = "附加集谐·偏移或造成谐度破坏伤害后，陆·赫斯攻击提升25%"
        attr.add_atk_percent(0.25, title, msg)

    # 设置角色谐度破坏
    if Interfered:
        title = "一场关于光的默辩"
        msg = "陆·赫斯在编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        if chain_num >= 6:
            title = f"{role_name}-六链"
            msg = "将目标当前的集谐·干涉提升2层，且此效果无视层数上限"
            attr.add_tune_strain_stack(2, title, msg)

        title = "一场关于光的默辩-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    chain_num = role.get_chain_num()
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "空中攻击伤害加成提升150%"
        attr.add_dmg_bonus(1.5, title, msg)

    if chain_num >= 3:
        title = f"{role_name}-三链"
        msg = "空中攻击·判决大地裂响和日髓阵列伤害倍率提升136%"
        attr.add_skill_ratio_in_skill_description(1.36, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队中角色造成谐度破坏伤害后使队中所有角色伤害提升20%，无法叠加"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "队中角色造成谐度破坏伤害时使陆·赫斯空中攻击·判决大地裂响的伤害提升30%"
        attr.add_dmg_bonus(0.3, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_damage]
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
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = False, Interfered: bool = False
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
    skill_multi = skill_damage_calc(char_result.skillTrees, SkillTreeMap[skill_type], "25", skillLevel)
    title = "于永冻中释义"
    msg = f"技能倍率{skill_multi}"
    attr.add_skill_multi(skill_multi, title, msg)

    # 附加集谐·偏移
    title = f"{role_name}-常态"
    msg = "特定攻击为命中目标附加【集谐·偏移】"
    attr.set_env_tune_strain()
    attr.add_effect(title, msg)

    title = "终局之释义"
    msg = "使共鸣解放于永冻中释义伤害倍率提升25%，叠加3层"
    attr.add_skill_ratio_in_skill_description(0.25 * 3, title, msg)

    chain_num = role.get_chain_num()

    # 设置角色固有技能
    role_breach = role.role.breach
    if role_breach and role_breach >= 4:
        if attr.env_tune_strain:
            title = "固有技能-无因的医谕"
            max_deepen = 0.3
            deepen_per_TBB = 0.05

            if chain_num >= 2:
                title = "固有技能-二链-无因的医谕"
                max_deepen = 0.6
                deepen_per_TBB = 0.1

            deepen = min(max_deepen, (attr.tune_break_boost // 10) * deepen_per_TBB)
            msg = f"每10点谐度破坏增幅使伤害加深{deepen_per_TBB * 100:.0f}%，最高{max_deepen * 100:.0f}%。当前提升{deepen * 100:.2f}%"
            attr.add_dmg_deepen(deepen, title, msg)

        title = "固有技能-无因的医谕"
        msg = "附加集谐·偏移或造成谐度破坏伤害后，陆·赫斯攻击提升25%"
        attr.add_atk_percent(0.25, title, msg)

    # 设置角色谐度破坏
    if Interfered:
        title = "一场关于光的默辩"
        msg = "陆·赫斯在编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

        if chain_num >= 6:
            title = f"{role_name}-六链"
            msg = "将目标当前的集谐·干涉提升2层，且此效果无视层数上限"
            attr.add_tune_strain_stack(2, title, msg)

        title = "一场关于光的默辩-响应集谐干涉"
        dmg = f"0.12% * {attr.tune_strain_stack} * {attr.tune_break_boost}"
        msg = f"每层集谐·干涉,每点谐度破坏增幅最终伤害提升{dmg}"
        attr.add_final_damage(calc_percent_expression(dmg), title, msg)

    # 设置角色技能施放是不是也有加成 eg：守岸人

    # 设置声骸属性
    attr.set_phantom_dmg_bonus()

    # 设置共鸣链
    if chain_num >= 1:
        title = f"{role_name}-一链"
        msg = "空中攻击伤害加成提升150%"
        attr.add_dmg_bonus(1.5, title, msg)

    if chain_num >= 2:
        title = f"{role_name}-二链"
        msg = "共鸣解放于永冻中释义伤害倍率提升60%"
        attr.add_skill_ratio_in_skill_description(0.6, title, msg)

    if chain_num >= 4:
        title = f"{role_name}-四链"
        msg = "队中角色造成谐度破坏伤害后使队中所有角色伤害提升20%，无法叠加"
        attr.add_dmg_bonus(0.2, title, msg)

    if chain_num >= 6:
        title = f"{role_name}-六链"
        msg = "终局之释义额外使共鸣解放于永冻中释义伤害加成提升40%*3"
        attr.add_dmg_bonus(0.4 * 3, title, msg)

    # 设置角色施放技能
    damage_func = [cast_attack, cast_liberation, cast_damage]
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
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True, Interfered: bool = False
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 琳奈buff
    lynae_buff(attr, 0, 1, isGroup)

    return calc_damage_2(attr, role, isGroup, Interfered)


def calc_damage_11(
    attr: DamageAttribute, role: RoleDetailData, isGroup: bool = True, Interfered: bool = False
) -> tuple[str, str]:
    # 设置角色伤害类型
    attr.set_char_damage(attack_damage)
    attr.set_char_template("temp_atk")

    # 莫宁buff
    mornye_buff(attr, 0, 1, isGroup)

    # 琳奈buff
    lynae_buff(attr, 0, 1, isGroup)

    return calc_damage_4(attr, role, isGroup, Interfered)


damage_detail = [
    {
        "title": "普攻·流金贯行",
        "func": lambda attr, role: calc_damage_1(attr, role),
    },
    {
        "title": "斩杀日冕·曜",
        "func": lambda attr, role: calc_damage_2(attr, role),
    },
    {
        "title": "空中攻击·判决大地裂响",
        "func": lambda attr, role: calc_damage_3(attr, role),
    },
    {
        "title": "于永冻中释义",
        "func": lambda attr, role: calc_damage_4(attr, role),
    },
    {
        "title": "响应集谐·斩杀日冕·曜",
        "func": lambda attr, role: calc_damage_2(attr, role, Interfered=True),
    },
    {
        "title": "响应集谐·于永冻中释义",
        "func": lambda attr, role: calc_damage_4(attr, role, Interfered=True),
    },
    {
        "title": "01莫/01琳/响应·斩杀日冕·曜",
        "func": lambda attr, role: calc_damage_10(attr, role, Interfered=True),
    },
    {
        "title": "01莫/01琳/响应·于永冻中释义",
        "func": lambda attr, role: calc_damage_11(attr, role, Interfered=True),
    },
]

rank = damage_detail[3]
