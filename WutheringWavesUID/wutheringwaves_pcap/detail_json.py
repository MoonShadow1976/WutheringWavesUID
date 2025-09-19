# 副词条属性映射 （小词条） e.g.  1, 2, 3
sub_props = {
    1: {"name": "生命", "isPercent": False},
    2: {"name": "攻击", "isPercent": False},
    3: {"name": "防御", "isPercent": False},
    4: {"name": "生命", "isPercent": True},
    5: {"name": "攻击", "isPercent": True},
    6: {"name": "防御", "isPercent": True},
    7: {"name": "共鸣技能伤害加成", "isPercent": True},
    8: {"name": "普攻伤害加成", "isPercent": True},
    9: {"name": "重击伤害加成", "isPercent": True},
    10: {"name": "共鸣解放伤害加成", "isPercent": True},
    11: {"name": "暴击", "isPercent": True},
    12: {"name": "暴击伤害", "isPercent": True},
    13: {"name": "共鸣效率", "isPercent": True},
}

# 主词条属性映射（大词条） e.g.  5001, 4018
main_first_props = {
    1: {"name": "暴击", "isPercent": True},
    2: {"name": "暴击伤害", "isPercent": True},
    3: {"name": "攻击", "isPercent": True}, # x
    4: {"name": "生命", "isPercent": True},
    5: {"name": "防御", "isPercent": True}, # x
    6: {"name": "治疗效果加成", "isPercent": True},
    7: {"name": "冷凝伤害加成", "isPercent": True},
    8: {"name": "热熔伤害加成", "isPercent": True},
    9: {"name": "导电伤害加成", "isPercent": True},
    10: {"name": "气动伤害加成", "isPercent": True},
    11: {"name": "衍射伤害加成", "isPercent": True},
    12: {"name": "湮灭伤害加成", "isPercent": True},
    13: {"name": "攻击", "isPercent": True},
    14: {"name": "生命", "isPercent": True}, # x
    15: {"name": "防御", "isPercent": True}, # x
    16: {"name": "共鸣效率", "isPercent": True},
    17: {"name": "攻击", "isPercent": True},
    18: {"name": "生命", "isPercent": True},
    19: {"name": "防御", "isPercent": True},
}

# 次主词条属性映射（小词条） e.g.  50001, 40001
main_second_props = {
    1: {"name": "攻击", "isPercent": False},
    2: {"name": "生命", "isPercent": False},
    3: {"name": "攻击", "isPercent": False},
}

# 用不上了
supplementary_props = {
    1: {"name": "生命", "isPercent": False},
    2: {"name": "攻击", "isPercent": False},
    3: {"name": "防御", "isPercent": False},
    4: {"name": "生命", "isPercent": True},
    5: {"name": "攻击", "isPercent": True},
    6: {"name": "防御", "isPercent": True},
    7: {"name": "共鸣技能伤害加成", "isPercent": True},
    8: {"name": "普攻伤害加成", "isPercent": True},
    9: {"name": "重击伤害加成", "isPercent": True},
    10: {"name": "共鸣解放伤害加成", "isPercent": True},
    11: {"name": "暴击", "isPercent": True},
    12: {"name": "暴击伤害", "isPercent": True},
    13: {"name": "共鸣效率", "isPercent": True},
    2018: {"name": "生命", "isPercent": True},
    20002: {"name": "生命", "isPercent": False},
    4003: {"name": "攻击", "isPercent": True}, # x
    40001: {"name": "攻击", "isPercent": False}, # x
    5001: {"name": "暴击", "isPercent": True},
    5002: {"name": "暴击伤害", "isPercent": True},
    5003: {"name": "攻击", "isPercent": True}, # x
    5004: {"name": "生命", "isPercent": True},
    5005: {"name": "防御", "isPercent": True}, # x
    50001: {"name": "攻击", "isPercent": False},
    50002: {"name": "生命", "isPercent": False},
    50003: {"name": "攻击", "isPercent": False},
    5006: {"name": "治疗效果加成", "isPercent": True},
    5007: {"name": "冷凝伤害加成", "isPercent": True},
    5008: {"name": "热熔伤害加成", "isPercent": True},
    5009: {"name": "导电伤害加成", "isPercent": True},
    5010: {"name": "气动伤害加成", "isPercent": True},
    5011: {"name": "衍射伤害加成", "isPercent": True},
    5012: {"name": "湮灭伤害加成", "isPercent": True},
    5013: {"name": "攻击", "isPercent": True},
    5014: {"name": "生命", "isPercent": True}, # x
    5015: {"name": "防御", "isPercent": True}, # x
    5016: {"name": "共鸣效率", "isPercent": True},
    5017: {"name": "攻击", "isPercent": True},
    5018: {"name": "生命", "isPercent": True},
    5019: {"name": "防御", "isPercent": True},
}

m_id2monsterId_strange = {
    "6000026": 390070075,  # "碎獠猪",
    "6000023": 390070071,  # "巡徊猎手",
    "6000017": 390077017,  # "湮灭棱镜",
    "6000015": 390077012,  # "热熔棱镜",
    "6000021": 390077025,  # "冥渊守卫",
    "6000029": 390077028,  # "绿熔蜥",
    "6000002": 390070052,  # "裂变幼岩",
    "6000008": 390070068,  # "呼咻咻",
    "6000028": 390070078,  # "绿熔蜥（稚形）",
    "6000011": 390070076,  # "咕咕河豚",
    "6000010": 390070070,  # "破霜猎手",
    "6000012": 390077004,  # "紫羽鹭",
    "6000007": 390070067,  # "阿嗞嗞",
    "6000027": 390070077,  # "遁地鼠",
    "6000025": 390070074,  # "游弋蝶",
    "6000033": 390077038,  # "箭簇熊",
    "6000018": 390077021,  # "坚岩斗士",
    "6000024": 390077024,  # "磐石守卫",
    "6000035": 390077033,  # "暗鬃狼",
    "6000031": 390077029,  # "刺玫菇",
    "6000037": 390080005,  # "鸣钟之龟",
    "6000001": 390070051,  # "先锋幼岩",
    "6000032": 390080007,  # "燎照之骑",
    "6000030": 390070079,  # "刺玫菇（稚形）",
    "6000005": 390070065,  # "审判战士",
    "6000009": 390070069,  # "呜咔咔",
    "6000016": 390077016,  # "衍射棱镜",
    "6000006": 390070066,  # "咔嚓嚓",
    "6000022": 390080003,  # "云闪之鳞",
    "6000004": 390070064,  # "鸣泣战士",
    "6000003": 390070053,  # "惊蛰猎手",
    "6000034": 390070105,  # "寒霜陆龟",
    "6000036": 390070100,  # "火鬃狼",
    "6000013": 390077005,  # "青羽鹭",
    "6000014": 390077013,  # "冷凝棱镜",
    "6000020": 390077023,  # "振铎乐师",
    "6000019": 390077022,  # "奏谕乐师",
}

#   "6000168": "梦魇·绿熔蜥",
#   "6000167": "共鸣回响·鸣式·利维亚坦",
#   "6000170": "梦魇·刺玫菇（稚形）",
#   "6000169": "梦魇·绿熔蜥（稚形）",