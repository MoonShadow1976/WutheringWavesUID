NORMAL_LIST = [
    "凌阳",
    "安可",
    "卡卡罗",
    "鉴心",
    "维里奈",
    "漂泊者·衍射",
    "漂泊者·湮灭",
    "千古洑流",
    "停驻之烟",
    "擎渊怒涛",
    "漪澜浮录",
    "浩境粼光",
]

card_sort_map = {
    "生命": "0",
    "攻击": "0",
    "防御": "0",
    "共鸣效率": "0%",
    "暴击": "0.0%",
    "暴击伤害": "0.0%",
    "属性伤害加成": "0.0%",
    "治疗效果加成": "0.0%",
    "普攻伤害加成": "0.0%",
    "重击伤害加成": "0.0%",
    "共鸣技能伤害加成": "0.0%",
    "共鸣解放伤害加成": "0.0%",
}

ATTRIBUTE_ID_MAP = {1: "冷凝", 2: "热熔", 3: "导电", 4: "气动", 5: "衍射", 6: "湮灭"}
WEAPON_TYPE_ID_MAP = {1: "长刃", 2: "迅刀", 3: "佩枪", 4: "臂铠", 5: "音感仪"}
DEAFAULT_WEAPON_ID = {1: 21010011, 2: 21020011, 3: 21030011, 4: 21040011, 5: 21050011}
SKILL_MAP = {
    "常态攻击": "1",
    "共鸣技能": "2",
    "共鸣回路": "7",
    "共鸣解放": "3",
    "变奏技能": "6",
    "延奏技能": "8",
}

SPECIAL_CHAR = {
    "1501": ["1501", "1502"],  # 光主
    "1502": ["1501", "1502"],
    "1604": ["1604", "1605"],  # 暗主
    "1605": ["1604", "1605"],
}

SPECIAL_CHAR_INT = {
    1501: [1501, 1502],  # 光主
    1502: [1501, 1502],
    1604: [1604, 1605],  # 暗主
    1605: [1604, 1605],
}
SPECIAL_CHAR_NAME = {
    "1501": "光主",
    "1502": "光主",
    "1604": "暗主",
    "1605": "暗主",
}
SPECIAL_CHAR_ID = {
    "漂泊者·衍射·男": "1501",
    "漂泊者·衍射·女": "1502",
    "漂泊者·湮灭·男": "1605",
    "漂泊者·湮灭·女": "1604",
}

NAME_ALIAS = {"漂泊者·湮灭": "暗主", "漂泊者·衍射": "光主"}


SONATA_FIRST_ID = {
    "凝夜白霜": [6000044],
    "熔山裂谷": [6000091, 390080007],
    "彻空冥雷": [390080003, 6000039, 6000088, 6000089],
    "啸谷长风": [6000086, 6000043],
    "浮星祛暗": [6000059],
    "沉日劫明": [6000090, 6000053, 6000042],
    "隐世回光": [6000060, 390080005],
    "轻云出月": [6000052, 390080005],
    "不绝余音": [6000048],
    "凌冽决断之心": [6000083],
    "高天共奏之曲": [6000085],
    "幽夜隐匿之帷": [6000082, 6000087],
    "此间永驻之光": [6000092],
    "无惧浪涛之勇": [6000084],
}
