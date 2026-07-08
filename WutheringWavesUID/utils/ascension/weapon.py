import copy
from pathlib import Path

from gsuid_core.logger import logger
from msgspec import json as msgjson

from ..ascension.constant import fixed_name
from .model import WeaponModel

MAP_PATH = Path(__file__).parent.parent / "map/detail_json/weapon"
weapon_id_data = {}


def read_weapon_json_files(directory):
    files = directory.rglob("*.json")

    for file in files:
        try:
            with open(file, encoding="utf-8") as f:
                data = msgjson.decode(f.read())
                file_name = file.name.split(".")[0]
                weapon_id_data[file_name] = data
        except Exception as e:
            logger.exception(f"read_weapon_json_files load fail decoding {file}", e)


read_weapon_json_files(MAP_PATH)


class WavesWeaponResult:
    def __init__(self):
        self.name: str = ""
        self.starLevel: int = 4
        self.type: int = 0
        self.stats = []
        self.param = []
        self.effect: str = ""
        self.effectName: str = ""
        self.sub_effect = {}
        self.resonLevel: int = 1

    def get_resonLevel_name(self):
        return f"谐振{['一', '二', '三', '四', '五'][self.resonLevel - 1]}阶"


def get_breach(breach: int | None, level: int):
    if breach is None:
        if level <= 20:
            breach = 0
        elif level <= 40:
            breach = 1
        elif level <= 50:
            breach = 2
        elif level <= 60:
            breach = 3
        elif level <= 70:
            breach = 4
        elif level <= 80:
            breach = 5
        elif level <= 90:
            breach = 6
    return breach


def get_weapon_detail(
    weapon_id: str | int,
    level: int,
    breach: int | None = None,
    resonLevel: int | None = 1,
) -> WavesWeaponResult:
    """
    breach 突破
    resonLevel 精炼
    """
    result = WavesWeaponResult()
    if str(weapon_id) not in weapon_id_data:
        return result

    breach = get_breach(breach, level)

    weapon_data = weapon_id_data[str(weapon_id)]
    result.name = weapon_data["name"]
    result.starLevel = weapon_data["starLevel"]
    result.type = weapon_data["type"]
    result.effectName = weapon_data["effectName"]
    result.stats = copy.deepcopy(weapon_data["stats"][str(breach)][str(level)])
    result.param = weapon_data["param"]
    effect = weapon_data["effect"]
    if resonLevel is None:
        resonLevel = 1
    result.resonLevel = resonLevel
    for i, p in enumerate(weapon_data["param"]):
        _temp = "{" + str(i) + "}"
        effect = effect.replace(f"{_temp}", str(p[resonLevel - 1]))
    result.effect = effect

    for stat in result.stats:
        if stat["isPercent"]:
            stat["value"] = f"{stat['value'] / 100:.1f}%"
        elif stat["isRatio"]:
            stat["value"] = f"{stat['value'] * 100:.1f}%"
        else:
            stat["value"] = f"{int(stat['value'])}"

    result.sub_effect = {}
    for i, v in enumerate(fixed_name):
        if result.effect.startswith(v):
            value = weapon_data["param"][0][resonLevel - 1]
            name = v.replace("提升", "").replace("全", "")
            result.sub_effect = {"name": name, "value": f"{value}"}

    return result


def get_weapon_id(weapon_name):
    return next(
        (_id for _id, value in weapon_id_data.items() if value["name"] == weapon_name),
        None,
    )


def get_weapon_star(weapon_name) -> int:
    weapon_id = get_weapon_id(weapon_name)
    if weapon_id is None:
        return 4

    result = get_weapon_detail(weapon_id, 90)
    if result is None:
        return 4
    return result.starLevel


def get_weapon_model(weapon_id: int | str) -> WeaponModel | None:
    if str(weapon_id) not in weapon_id_data:
        return None
    return WeaponModel(**weapon_id_data[str(weapon_id)])


class WeaponExp:
    """武器经验计算器"""

    # 武器升级所需经验：星级 -> {等级: 经验值}
    LEVEL_COST: dict[int, dict[str, int]] = {
        1: {
            "1": 160,
            "2": 200,
            "3": 280,
            "4": 320,
            "5": 400,
            "6": 440,
            "7": 520,
            "8": 600,
            "9": 640,
            "10": 720,
            "11": 800,
            "12": 880,
            "13": 960,
            "14": 1080,
            "15": 1160,
            "16": 1240,
            "17": 1360,
            "18": 1440,
            "19": 1560,
            "20": 1680,
            "21": 1760,
            "22": 1880,
            "23": 2000,
            "24": 2160,
            "25": 2280,
            "26": 2400,
            "27": 2560,
            "28": 2680,
            "29": 2840,
            "30": 3000,
            "31": 3160,
            "32": 3320,
            "33": 3520,
            "34": 3680,
            "35": 3880,
            "36": 4080,
            "37": 4280,
            "38": 4480,
            "39": 4680,
            "40": 4920,
            "41": 5120,
            "42": 5360,
            "43": 5600,
            "44": 5880,
            "45": 6120,
            "46": 6400,
            "47": 6680,
            "48": 6960,
            "49": 7280,
            "50": 7560,
            "51": 7880,
            "52": 8200,
            "53": 8560,
            "54": 8880,
            "55": 9240,
            "56": 9640,
            "57": 10000,
            "58": 10400,
            "59": 10800,
            "60": 11240,
            "61": 11680,
            "62": 12120,
            "63": 12560,
            "64": 13040,
            "65": 13520,
            "66": 14040,
            "67": 14560,
            "68": 15080,
            "69": 15600,
            "70": 16200,
            "71": 16760,
            "72": 17360,
            "73": 17960,
            "74": 18600,
            "75": 19240,
            "76": 19920,
            "77": 20600,
            "78": 21280,
            "79": 22000,
            "80": 24200,
            "81": 25280,
            "82": 26800,
            "83": 28840,
            "84": 31480,
            "85": 34880,
            "86": 39160,
            "87": 44560,
            "88": 51200,
            "89": 59360,
            "90": 0,
        },
        2: {
            "1": 200,
            "2": 250,
            "3": 350,
            "4": 400,
            "5": 500,
            "6": 550,
            "7": 650,
            "8": 750,
            "9": 800,
            "10": 900,
            "11": 1000,
            "12": 1100,
            "13": 1200,
            "14": 1350,
            "15": 1450,
            "16": 1550,
            "17": 1700,
            "18": 1800,
            "19": 1950,
            "20": 2100,
            "21": 2200,
            "22": 2350,
            "23": 2500,
            "24": 2700,
            "25": 2850,
            "26": 3000,
            "27": 3200,
            "28": 3350,
            "29": 3550,
            "30": 3750,
            "31": 3950,
            "32": 4150,
            "33": 4400,
            "34": 4600,
            "35": 4850,
            "36": 5100,
            "37": 5350,
            "38": 5600,
            "39": 5850,
            "40": 6150,
            "41": 6400,
            "42": 6700,
            "43": 7000,
            "44": 7350,
            "45": 7650,
            "46": 8000,
            "47": 8350,
            "48": 8700,
            "49": 9100,
            "50": 9450,
            "51": 9850,
            "52": 10250,
            "53": 10700,
            "54": 11100,
            "55": 11550,
            "56": 12050,
            "57": 12500,
            "58": 13000,
            "59": 13500,
            "60": 14050,
            "61": 14600,
            "62": 15150,
            "63": 15700,
            "64": 16300,
            "65": 16900,
            "66": 17550,
            "67": 18200,
            "68": 18850,
            "69": 19500,
            "70": 20250,
            "71": 20950,
            "72": 21700,
            "73": 22450,
            "74": 23250,
            "75": 24050,
            "76": 24900,
            "77": 25750,
            "78": 26600,
            "79": 27500,
            "80": 30250,
            "81": 31600,
            "82": 33500,
            "83": 36050,
            "84": 39350,
            "85": 43600,
            "86": 48950,
            "87": 55700,
            "88": 64000,
            "89": 74200,
            "90": 0,
        },
        3: {
            "1": 240,
            "2": 300,
            "3": 420,
            "4": 480,
            "5": 600,
            "6": 660,
            "7": 780,
            "8": 900,
            "9": 960,
            "10": 1080,
            "11": 1200,
            "12": 1320,
            "13": 1440,
            "14": 1620,
            "15": 1740,
            "16": 1860,
            "17": 2040,
            "18": 2160,
            "19": 2340,
            "20": 2520,
            "21": 2640,
            "22": 2820,
            "23": 3000,
            "24": 3240,
            "25": 3420,
            "26": 3600,
            "27": 3840,
            "28": 4020,
            "29": 4260,
            "30": 4500,
            "31": 4740,
            "32": 4980,
            "33": 5280,
            "34": 5520,
            "35": 5820,
            "36": 6120,
            "37": 6420,
            "38": 6720,
            "39": 7020,
            "40": 7380,
            "41": 7680,
            "42": 8040,
            "43": 8400,
            "44": 8820,
            "45": 9180,
            "46": 9600,
            "47": 10020,
            "48": 10440,
            "49": 10920,
            "50": 11340,
            "51": 11820,
            "52": 12300,
            "53": 12840,
            "54": 13320,
            "55": 13860,
            "56": 14460,
            "57": 15000,
            "58": 15600,
            "59": 16200,
            "60": 16860,
            "61": 17520,
            "62": 18180,
            "63": 18840,
            "64": 19560,
            "65": 20280,
            "66": 21060,
            "67": 21840,
            "68": 22620,
            "69": 23400,
            "70": 24300,
            "71": 25140,
            "72": 26040,
            "73": 26940,
            "74": 27900,
            "75": 28860,
            "76": 29880,
            "77": 30900,
            "78": 31920,
            "79": 33000,
            "80": 36300,
            "81": 37920,
            "82": 40200,
            "83": 43260,
            "84": 47220,
            "85": 52320,
            "86": 58740,
            "87": 66840,
            "88": 76800,
            "89": 89040,
            "90": 0,
        },
        4: {
            "1": 400,
            "2": 500,
            "3": 700,
            "4": 800,
            "5": 1000,
            "6": 1100,
            "7": 1300,
            "8": 1500,
            "9": 1600,
            "10": 1800,
            "11": 2000,
            "12": 2200,
            "13": 2400,
            "14": 2700,
            "15": 2900,
            "16": 3100,
            "17": 3400,
            "18": 3600,
            "19": 3900,
            "20": 4200,
            "21": 4400,
            "22": 4700,
            "23": 5000,
            "24": 5400,
            "25": 5700,
            "26": 6000,
            "27": 6400,
            "28": 6700,
            "29": 7100,
            "30": 7500,
            "31": 7900,
            "32": 8300,
            "33": 8800,
            "34": 9200,
            "35": 9700,
            "36": 10200,
            "37": 10700,
            "38": 11200,
            "39": 11700,
            "40": 12300,
            "41": 12800,
            "42": 13400,
            "43": 14000,
            "44": 14700,
            "45": 15300,
            "46": 16000,
            "47": 16700,
            "48": 17400,
            "49": 18200,
            "50": 18900,
            "51": 19700,
            "52": 20500,
            "53": 21400,
            "54": 22200,
            "55": 23100,
            "56": 24100,
            "57": 25000,
            "58": 26000,
            "59": 27000,
            "60": 28100,
            "61": 29200,
            "62": 30300,
            "63": 31400,
            "64": 32600,
            "65": 33800,
            "66": 35100,
            "67": 36400,
            "68": 37700,
            "69": 39000,
            "70": 40500,
            "71": 41900,
            "72": 43400,
            "73": 44900,
            "74": 46500,
            "75": 48100,
            "76": 49800,
            "77": 51500,
            "78": 53200,
            "79": 55000,
            "80": 60500,
            "81": 63200,
            "82": 67000,
            "83": 72100,
            "84": 78700,
            "85": 87200,
            "86": 97900,
            "87": 111400,
            "88": 128000,
            "89": 148400,
            "90": 0,
        },
        5: {
            "1": 600,
            "2": 700,
            "3": 800,
            "4": 900,
            "5": 1000,
            "6": 1100,
            "7": 1300,
            "8": 1400,
            "9": 1600,
            "10": 1800,
            "11": 2000,
            "12": 2200,
            "13": 2500,
            "14": 2700,
            "15": 3000,
            "16": 3300,
            "17": 3600,
            "18": 3900,
            "19": 4300,
            "20": 4600,
            "21": 5000,
            "22": 5400,
            "23": 5800,
            "24": 6300,
            "25": 6700,
            "26": 7200,
            "27": 7700,
            "28": 8200,
            "29": 8700,
            "30": 9300,
            "31": 9900,
            "32": 10500,
            "33": 11100,
            "34": 11800,
            "35": 12400,
            "36": 13100,
            "37": 13800,
            "38": 14600,
            "39": 15300,
            "40": 16100,
            "41": 16900,
            "42": 17700,
            "43": 18600,
            "44": 19400,
            "45": 20300,
            "46": 21300,
            "47": 22200,
            "48": 23200,
            "49": 24200,
            "50": 25200,
            "51": 26300,
            "52": 27300,
            "53": 28400,
            "54": 29600,
            "55": 30700,
            "56": 31900,
            "57": 33100,
            "58": 34300,
            "59": 35600,
            "60": 36900,
            "61": 38200,
            "62": 39600,
            "63": 41000,
            "64": 42400,
            "65": 43800,
            "66": 45300,
            "67": 46800,
            "68": 48300,
            "69": 49800,
            "70": 51400,
            "71": 53000,
            "72": 54700,
            "73": 56400,
            "74": 58100,
            "75": 59800,
            "76": 61600,
            "77": 63400,
            "78": 65200,
            "79": 67100,
            "80": 71600,
            "81": 73900,
            "82": 76900,
            "83": 80600,
            "84": 85300,
            "85": 91400,
            "86": 99000,
            "87": 108400,
            "88": 120000,
            "89": 134100,
            "90": 0,
        },
    }

    # 武器经验瓶配置：经验值 -> {id, cost}
    EXP_ITEM: dict[int, dict[str, int]] = {
        1000: {"id": 43020001, "cost": 400},
        3000: {"id": 43020002, "cost": 1200},
        8000: {"id": 43020003, "cost": 3200},
        20000: {"id": 43020004, "cost": 8000},
    }

    @classmethod
    def get_level_up_exp(cls, star_level: int | str, head_level: int | str, tail_level: int | str) -> int:
        """计算指定星级武器从 head_level 升到 tail_level 所需总经验"""
        cost_dict = cls.LEVEL_COST[int(star_level)]
        total = 0
        for level in range(int(head_level), int(tail_level)):
            total += cost_dict.get(str(level), 0)
        return total

    @classmethod
    def get_cost_from_exp(cls, total_exp: int) -> list[dict[str, int]]:
        """
        根据总经验值返回所需经验瓶列表（按优先级：金瓶 > 紫瓶 > 蓝瓶 > 绿瓶），
        绿瓶允许溢出。最后附加一个汇总条目 {"id": 2, "num": 总cost}。
        """
        exp_values = sorted(cls.EXP_ITEM.keys(), reverse=True)
        min_exp_value = exp_values[-1]
        normal_exp_values = exp_values[:-1]  # 除最低级外的其他瓶子

        result = []
        total_cost = 0

        for exp in normal_exp_values:
            count = total_exp // exp
            if count > 0:
                total_exp %= exp
                result.append({"id": cls.EXP_ITEM[exp]["id"], "num": count})
                total_cost += count * cls.EXP_ITEM[exp]["cost"]

        green_count = (total_exp + min_exp_value - 1) // min_exp_value
        if green_count > 0:  # 处理最低级瓶子（向上取整，允许溢出）
            result.append({"id": cls.EXP_ITEM[min_exp_value]["id"], "num": green_count})
            total_cost += green_count * cls.EXP_ITEM[min_exp_value]["cost"]

        if total_cost > 0:
            result.append({"id": 2, "num": total_cost})
        return result
