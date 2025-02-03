import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from gsuid_core.data_store import get_res_path

MAIN_PATH = get_res_path() / "WutheringWavesUID"
sys.path.append(str(MAIN_PATH))

# 配置文件
CONFIG_PATH = MAIN_PATH / "config.json"

# 用户数据保存文件
PLAYER_PATH = MAIN_PATH / "players"

# 游戏素材
RESOURCE_PATH = MAIN_PATH / "resource"
PHANTOM_PATH = RESOURCE_PATH / "phantom"
FETTER_PATH = RESOURCE_PATH / "fetter"
AVATAR_PATH = RESOURCE_PATH / "waves_avatar"
WEAPON_PATH = RESOURCE_PATH / "waves_weapon"
ROLE_PILE_PATH = RESOURCE_PATH / "role_pile"
ROLE_DETAIL_PATH = RESOURCE_PATH / "role_detail"
ROLE_DETAIL_SKILL_PATH = ROLE_DETAIL_PATH / "skill"
ROLE_DETAIL_CHAINS_PATH = ROLE_DETAIL_PATH / "chains"

# 攻略
GUIDE_PATH = MAIN_PATH / "guide_new"
# 小沐XMu 攻略库
XMU_GUIDE_PATH = GUIDE_PATH / "XMu"
# Moealkyne 攻略库
MOEALKYNE_GUIDE_PATH = GUIDE_PATH / "Moealkyne"
# 金铃子攻略组 攻略库
JINLINGZI_GUIDE_PATH = GUIDE_PATH / "JinLingZi"
# 結星 攻略库
JIEXING_GUIDE_PATH = GUIDE_PATH / "JieXing"

GUIDE_CONFIG_MAP = {
    "小沐XMu": (XMU_GUIDE_PATH, 10450567, "kuro"),
    "Moealkyne": (MOEALKYNE_GUIDE_PATH, 533395803, "tap"),
    "金铃子攻略组": (JINLINGZI_GUIDE_PATH, 487275027, "bilibili"),
    "結星": (JIEXING_GUIDE_PATH, 10015697, "kuro"),
}

# 自定义背景图
CUSTOM_CARD_PATH = MAIN_PATH / "custom_role_pile"

# 其他的素材
OTHER_PATH = MAIN_PATH / "other"
CALENDAR_PATH = OTHER_PATH / "calendar"


def init_dir():
    for i in [
        MAIN_PATH,
        PLAYER_PATH,
        RESOURCE_PATH,
        PHANTOM_PATH,
        FETTER_PATH,
        AVATAR_PATH,
        WEAPON_PATH,
        ROLE_PILE_PATH,
        ROLE_DETAIL_PATH,
        ROLE_DETAIL_SKILL_PATH,
        ROLE_DETAIL_CHAINS_PATH,
        GUIDE_PATH,
        XMU_GUIDE_PATH,
        MOEALKYNE_GUIDE_PATH,
        JINLINGZI_GUIDE_PATH,
        JIEXING_GUIDE_PATH,
        CUSTOM_CARD_PATH,
        OTHER_PATH,
        CALENDAR_PATH,
    ]:
        i.mkdir(parents=True, exist_ok=True)


init_dir()

# 设置 Jinja2 环境
TEMP_PATH = Path(__file__).parents[1].parent / "templates"
waves_templates = Environment(
    loader=FileSystemLoader(
        [
            str(TEMP_PATH),
        ]
    )
)
