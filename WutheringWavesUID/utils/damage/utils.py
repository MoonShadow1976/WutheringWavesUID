import re
from typing import Dict, Literal

SONATA_FREEZING = "凝夜白霜"
SONATA_MOLTEN = "熔山裂谷"
SONATA_VOID = "彻空冥雷"
SONATA_SIERRA = "啸谷长风"
SONATA_CELESTIAL = "浮星祛暗"
SONATA_SINKING = "沉日劫明"
SONATA_REJUVENATING = "隐世回光"
SONATA_MOONLIT = "轻云出月"
SONATA_LINGERING = "不绝余音"

CHAR_ATTR_FREEZING = "冷凝"
CHAR_ATTR_CELESTIAL = "衍射"
CHAR_ATTR_VOID = "导电"
CHAR_ATTR_MOLTEN = "热熔"
CHAR_ATTR_SIERRA = "气动"
CHAR_ATTR_SINKING = "湮灭"

# 普攻伤害加成
attack_damage = "attack_damage"
# 重击伤害加成
hit_damage = "hit_damage"
# 共鸣技能伤害加成
skill_damage = "skill_damage"
# 共鸣解放伤害加成
liberation_damage = "liberation_damage"
# 治疗效果加成
heal_bonus = "heal_bonus"
# 护盾量加成
shield_bonus = "shield_bonus"

# 造成伤害
cast_damage = "cast_damage"
# 造成普攻伤害
cast_attack = "cast_attack"
# 造成重击伤害
cast_hit = "cast_hit"
# 造成技能伤害
cast_skill = "cast_skill"
# 释放解放伤害
cast_liberation = "cast_liberation"
# 施放闪避反击
cast_dodge_counter = "cast_dodge_counter"
# 施放变奏技能
cast_variation = "cast_variation"
# 共鸣技能造成治疗
skill_create_healing = "skill_create_healing"

# 定义一个类型别名
SkillType = Literal["常态攻击", "共鸣技能", "共鸣解放", "变奏技能", "共鸣回路"]

# 攻击模版
temp_atk = "temp_atk"
# 生命模版
temp_life = "temp_life"
# 防御模版
temp_def = "temp_def"

SkillTreeMap = {
    "常态攻击": "1",
    "共鸣技能": "2",
    "共鸣解放": "3",
    "变奏技能": "6",
    "共鸣回路": "7",
}


def skill_damage_calc(skillTree: Dict, skillTreeId: str, skillParamId: str, skillLevel: int) -> str:
    """
    获取技能伤害
    :param skillTree: 技能树
    :param skillTreeId: 技能树id
    :param skillParamId: 技能参数id
    :param skillLevel: 技能等级
    :return: 技能伤害
    """
    return skillTree[skillTreeId]["skill"]["level"][skillParamId]["param"][0][skillLevel]


def parse_skill_multi(temp):
    """
    解析 "1313+5.97%"
    """
    match = re.match(r'([0-9.]+)(\+([0-9.]+)%?)', temp)
    if match:
        value = float(match.group(1))  # 获取数字部分
        percent = float(match.group(3))  # 获取百分比部分
        return value, percent
    return 0, 0


def add_comma_separated_numbers(*nums: str) -> str:
    """
    接受多个带逗号的数字字符串，去除逗号后进行加法计算，并返回结果，结果也带逗号。
    :return: 计算后的整数和，格式化为带逗号的字符串
    """
    total = sum(float(num.replace(',', '')) for num in nums)
    return f"{total:,.0f}"
