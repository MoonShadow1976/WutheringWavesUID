import importlib
import os

from ....utils.damage.abstract import DamageDetailRegister, DamageRankRegister

CUR_PACKAGE = __package__

CURRENT_DIR = os.path.dirname(__file__)

# 特例映射：注册ID -> 实际使用的模块后缀（即 damage_ 后面的部分）
SPECIAL_ID_TO_MODULE = {
    "1408": "1406",  # 风主女 使用 风主男 的数据
    "1501": "1502",  # 光主男 使用 光主女 的数据
    "1605": "1604",  # 暗主男 使用 暗主女 的数据
    "1309": "1310",  # 雷主男 使用 雷主女 的数据
}


def _register_attr(attr_name, register_method):
    """
    自动扫描当前目录下所有 damage_*.py 模块，
    通过 importlib.import_module 导入（保持包上下文），
    提取指定属性（如 damage_detail 或 rank），
    并根据特例映射注册到对应的角色ID上。
    """
    for filename in os.listdir(CURRENT_DIR):
        if not filename.startswith("damage_") or not filename.endswith(".py"):
            continue

        # 模块名（不带 .py 后缀），例如 "damage_1102"
        module_name = filename[:-3]
        # 相对于当前包的导入路径，例如 ".damage_1102"
        relative_name = f".{module_name}"
        try:
            # 使用相对导入，保持包上下文，这样模块内部的相对导入（如 from ...api）就能正常工作
            module = importlib.import_module(relative_name, package=CUR_PACKAGE)
        except ImportError as e:
            raise ImportError(f"导入模块 {module_name} 失败: {e}") from e

        attr_value = getattr(module, attr_name, None)
        if attr_value is None:
            continue

        # 提取模块后缀（角色ID），如 "1102"
        module_suffix = module_name[7:]  # 去掉 "damage_"
        default_id = module_suffix

        # 收集所有需要注册到此模块数据的ID（默认ID + 指向该模块的特例ID）
        ids_to_register = {default_id}
        for reg_id, mod_suffix in SPECIAL_ID_TO_MODULE.items():
            if mod_suffix == default_id:
                ids_to_register.add(reg_id)

        for rid in ids_to_register:
            register_method(rid, attr_value)


def register_damage():
    """注册所有角色的伤害详情数据（damage_detail）"""
    _register_attr("damage_detail", DamageDetailRegister.register_class)


def register_rank():
    """注册所有角色的命座/排行数据（rank）"""
    _register_attr("rank", DamageRankRegister.register_class)
