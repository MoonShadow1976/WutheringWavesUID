"""队友说明图（``ww队友配置``）的数据来源。

探测逻辑放这里，需要的队友增益定义（装备目录、状态声明）从 buff.py 取，
不重复维护第二份。
"""

from .buff import (
    ALL_CATEGORIES,
    CASE_CHAIN,
    CASE_DAMAGE,
    CASE_ENV,
    CASE_TEMPLATE,
    CATEGORY_LABELS,
    EQUIP_KINDS,
    KIND_ECHO,
    KIND_LABELS,
    KIND_SONATA,
    KIND_WEAPON,
    TeamConfigError,
    TeamMember,
    _apply_member,
    _char_registry,
    _format_state,
    char_name,
    declared_cases,
    preset_names,
    state_hint,
    supported_teammate_ids,
    teammate_equip,
    teammate_states,
    weapon_options,
)
from .utils import temp_atk, temp_def, temp_life

# --------------------------------------------------------------- 配置自动生成
#
# 「ww队友配置」说明图里的内容全部由这里生成，不手写：
#   - 能开关哪几类        -> 独立对象执行各阶段，看实际新增效果
#   - 预设专武是哪把      -> 直接读 teammate_equip 声明
#   - 每条增益的生效条件  -> 遍历「主角色伤害类型 × 属性 × 模板 × 共鸣链」探测
#   - 可调状态            -> 直接读 Char_xxxx.teammate_states 声明


# 探测用的两个轴都取自现有配置，不手写：
#   主C属性  -> utils/resource/constant.py 的 ATTRIBUTE_ID_MAP
#   环境状态 -> DamageAttribute 上 set_env_* 的文档字符串（"光噪效应" 之类）


def detect_teammate(role_id: int) -> dict:
    """空跑探测一名队友实际提供什么、在什么条件下提供。"""
    from .abstract import WavesCharRegister

    role_id = int(role_id)
    char_clz = WavesCharRegister.find_class(role_id)
    if char_clz is None:
        raise TeamConfigError(f"未找到角色【{role_id}】")
    if role_id not in supported_teammate_ids():
        raise TeamConfigError(f"【{getattr(char_clz, 'name', role_id)}】暂不支持作为自定义队友")

    # 每条文案单独记录：同名的多种增益、六链数值变化不能互相覆盖。
    effects: dict[tuple[str, str, str, str], dict] = {}
    seen_category: set[str] = set()
    env_probes = _env_probes()
    state_probes = _state_probes(role_id)
    targets = getattr(char_clz, "teammate_targets", ())
    probe_role_id = targets[0] if targets else None
    for probe_index, states in enumerate(state_probes):
        for chain in _CHAIN_PROBES:
            member = TeamMember(
                role_id=role_id, chain=chain, states=states, weapon=False, name=getattr(char_clz, "name", str(role_id))
            )
            for template in _TEMPLATE_LABELS:
                for damage_type, damage_label in _damage_probes():
                    for char_attr in _attr_probes():
                        for extra in env_probes:
                            attr = _scratch_attr(damage_type, char_attr, extra, template, probe_role_id)
                            attr.add_teammate(role_id)
                            attr.group_mode = True
                            capture: dict[str, list[tuple[str, str]]] = {}
                            # 仅说明图的独立对象上执行，不改生产伤害方法或注册表。
                            _apply_member(attr, member, capture)
                            # 单独捕获默认专武的注册入口效果，为说明图附加来源标识。
                            start = len(attr.effect)
                            char_clz()._do_weapon(attr, chain=chain, resonLevel=member.reson_level, isGroup=True, states=states)
                            capture["weapon"] = [(effect.element_msg, effect.element_value) for effect in attr.effect[start:]]
                            combo = (damage_label, char_attr, template, tuple(sorted(extra)))
                            for category, entries in capture.items():
                                for title, msg in set(entries):
                                    # 无标题的纯数值写入已有 add_effect 解释，不单列。
                                    if not title:
                                        continue
                                    source = "weapon" if category == "weapon" else category
                                    category_key = "character" if source == "weapon" else category
                                    seen_category.add(category_key)
                                    info = effects.setdefault(
                                        (category_key, title, msg, source),
                                        {"chains": set(), "combos": set(), "states": set()},
                                    )
                                    info["chains"].add(chain)
                                    info["combos"].add(combo)
                                    info["states"].add(probe_index)

    declared = teammate_equip(role_id)
    declared_weapon = declared.get(KIND_WEAPON) or {}
    weapon_id = declared_weapon.get("id")
    weapon_name = weapon_name_of(weapon_id) if weapon_id else None

    equip = {
        "sonata": {"default": declared.get(KIND_SONATA), "options": preset_names(KIND_SONATA)},
        "echo": {"default": declared.get(KIND_ECHO), "options": preset_names(KIND_ECHO)},
        "weapon": {
            "default": weapon_name,
            "id": declared_weapon.get("id"),
            "declared": bool(declared_weapon),
            "options": [name for _id, name in weapon_options()],
        },
        # 条件套：满足条件时改带的那几套（默认值见上面的 default）
        "cases": equip_case_rows(declared),
    }

    categories: dict[str, dict] = {key: {"key": key, "label": label, "effects": []} for key, label in CATEGORY_LABELS.items()}
    for (category, title, msg, source), info in effects.items():
        if category not in categories:
            continue
        categories[category]["effects"].append(
            {
                "title": title,
                "msg": msg,
                "min_chain": min(info["chains"]),
                "chains": sorted(info["chains"]),
                "source": source,
                "state_hint": _effect_state_hint(info["states"], state_probes),
                "condition": _condition_text(info["combos"]),
            }
        )
    for key, category in categories.items():
        category["effects"].sort(key=lambda item: (item["min_chain"], item["title"], item["msg"]))
        category["available"] = key in seen_category

    attribute_id, attribute, weapon_type_id, weapon_type = _role_metadata(role_id)
    return {
        "role_id": role_id,
        "name": getattr(char_clz, "name", str(role_id)),
        "attribute_id": attribute_id,
        "attribute": attribute,
        "weapon_type_id": weapon_type_id,
        "weapon_type": weapon_type,
        "star_level": getattr(char_clz, "starLevel", None),
        "weapon_id": weapon_id,
        "weapon_name": weapon_name,
        "equip": equip,
        "categories": [categories[key] for key in ALL_CATEGORIES],
        "states": [{"key": key, "hint": state_hint(role_id, key), **spec} for key, spec in teammate_states(role_id).items()],
    }


def weapon_name_of(weapon_id: int) -> str | None:
    weapon_clz = _weapon_class(weapon_id)
    return getattr(weapon_clz, "name", None) if weapon_clz else None


_TEMPLATE_LABELS = {temp_atk: "攻击", temp_life: "生命", temp_def: "防御"}


def equip_case_rows(declared: dict) -> list[dict]:
    """条件套的展示行：什么条件下换成什么（说明图直接用，不手写文案）。"""
    rows: list[dict] = []
    for case in declared_cases(declared):
        pieces = [f"{KIND_LABELS[kind]}={case[kind]}" for kind in EQUIP_KINDS if case.get(kind)]
        weapon = case.get(KIND_WEAPON)
        if isinstance(weapon, dict) and weapon.get("id"):
            pieces.append(f"{KIND_LABELS[KIND_WEAPON]}={weapon_name_of(weapon['id']) or weapon['id']}")
        rows.append({"when": case_condition_text(case), "equip": " / ".join(pieces)})
    return rows


def case_condition_text(case: dict) -> str:
    """条件套的条件渲染成人话，取值说明都取自现成的名字表。"""
    damages = dict(_damage_probes())
    parts: list[str] = []
    env = case.get(CASE_ENV)
    if env:
        parts.append(f"主角色处于{_env_labels().get(env, env)}")
    damage = case.get(CASE_DAMAGE)
    if damage:
        parts.append(f"主角色是{damages.get(damage, damage)}")
    template = case.get(CASE_TEMPLATE)
    if template:
        parts.append(f"主角色模板是{_TEMPLATE_LABELS.get(template, template)}")
    chain = case.get(CASE_CHAIN)
    if chain is not None:
        parts.append(f"自身{_format_state(chain)}链起")
    return "、".join(parts) or "无条件"


def _weapon_class(weapon_id: int):
    from .abstract import WavesWeaponRegister

    return WavesWeaponRegister.find_class(int(weapon_id))


def _condition_text(combo_set: set) -> str:
    """按实际命中的主C上下文归并条件；不把无关环境误当作门槛。"""
    if not combo_set:
        return ""
    contexts: dict[tuple, set] = {}
    for damage, attribute, template, env in sorted(combo_set):
        contexts.setdefault((damage, attribute, template), set()).add(frozenset(env))

    # 空环境能生效就是无环境门槛。否则只保留最小的生效环境，
    # 比如「光噪」和「光噪+加深」都命中时，只写「光噪」。
    groups: dict[tuple, set] = {}
    for context, envs in contexts.items():
        minimal = tuple(sorted(tuple(sorted(env)) for env in envs if not any(other < env for other in envs)))
        groups.setdefault(minimal, set()).add(context)

    all_axes = ({label for _, label in _damage_probes()}, set(_attr_probes()), set(_TEMPLATE_LABELS))
    prefixes = ("主角色", "主角色属性", "主角色模板")
    clauses = []
    for envs, matched in groups.items():
        axes = tuple({context[i] for context in matched} for i in range(3))
        # 可以独立描述的笛卡尔积才压成轴条件；有交叉限制时不误写成任意组合。
        rectangular = len(matched) == len(axes[0]) * len(axes[1]) * len(axes[2])
        ranges = [axes] if rectangular else [tuple({value} for value in context) for context in sorted(matched)]
        for axis_values in ranges:
            parts = []
            for i, values in enumerate(axis_values):
                if values != all_axes[i]:
                    labels = [_TEMPLATE_LABELS[value] if i == 2 else value for value in sorted(values)]
                    parts.append(prefixes[i] + "/".join(labels))
            if envs != ((),):
                # 同一环境里基础效应与加深同时必需时，保留真正的较强条件。
                alternatives = []
                for env in envs:
                    flags = [key for key in env if f"{key}_deepen" not in env]
                    alternatives.append("且".join(_env_labels().get(key, key) for key in flags))
                parts.append("/".join(alternatives))
            clauses.append("；".join(parts))
    return " 或 ".join(clauses)


def _role_metadata(role_id: int) -> tuple[int | None, str, int | None, str]:
    """复用突破模块已经加载的元数据，不造属性对象、不重新读文件。"""
    from ..ascension.char import char_id_data
    from ..resource.constant import ATTRIBUTE_ID_MAP, WEAPON_TYPE_ID_MAP

    data = char_id_data.get(str(role_id), {})
    attribute_id = data.get("attributeId")
    weapon_type_id = data.get("weaponTypeId")
    return attribute_id, ATTRIBUTE_ID_MAP.get(attribute_id, ""), weapon_type_id, WEAPON_TYPE_ID_MAP.get(weapon_type_id, "")


def teammate_overview() -> list[dict]:
    """所有可作为自定义队友的角色一览（只读声明，不做昂贵探测）。

    同名条目（例如男女主角共用「漂泊者·气动」）按名字去重，保留 id 最小的那个，
    因为按名字查角色时也只会有唯一结果，列表里重复出现反而误导。
    """
    from .abstract import CharAbstract

    rows = {}
    for role_id in sorted(supported_teammate_ids()):
        char_clz = _char_registry().find_class(role_id)
        name = getattr(char_clz, "name", str(role_id))
        if name in rows:
            continue
        declared = teammate_equip(role_id)
        weapon = declared.get(KIND_WEAPON) or {}
        attribute_id, attribute, weapon_type_id, weapon_type = _role_metadata(role_id)
        rows[name] = {
            "role_id": role_id,
            "name": name,
            "star_level": getattr(char_clz, "starLevel", None),
            "states": list(teammate_states(role_id)),
            "state_defaults": {key: spec.get("default") for key, spec in teammate_states(role_id).items()},
            "attribute_id": attribute_id,
            "attribute": attribute,
            "weapon_type_id": weapon_type_id,
            "weapon_type": weapon_type,
            "equip": {
                "sonata": declared.get(KIND_SONATA),
                "echo": declared.get(KIND_ECHO),
                "weapon": weapon_name_of(weapon["id"]) if weapon.get("id") else None,
            },
            "has_outro": char_clz._do_outro is not CharAbstract._do_outro,
            "has_character_buff": char_clz._do_buff is not CharAbstract._do_buff,
            "has_weapon_buff": bool(weapon) or char_clz._do_weapon is not CharAbstract._do_weapon,
        }
    for row in rows.values():
        row["sources"] = [
            label
            for present, label in (
                (row["has_character_buff"], "角色"),
                (row["has_outro"], "延奏"),
                (row["has_weapon_buff"], "专武"),
                (bool(row["equip"]["sonata"]), "套装"),
                (bool(row["equip"]["echo"]), "声骸"),
            )
            if present
        ]
    return sorted(
        rows.values(),
        key=lambda row: (
            -min(5, int(row["star_level"] or 0)),
            row["attribute_id"] or 99,
            row["weapon_type_id"] or 99,
            row["role_id"],
        ),
    )


def example_commands(role_id: int, short_name: str = "") -> list[str]:
    role_id = int(role_id)
    name = short_name or char_name(role_id)
    # 示例也要能实际执行，主C不能与展示队友是同一角色。
    main = "今汐" if role_id == 1311 else "心"
    base = f"ww{main}伤害3 换队友 {name}01"
    sample = "延奏=关"
    for key, spec in teammate_states(role_id).items():
        default = spec.get("default")
        if spec.get("type") == "bool":
            pick = not default
        elif spec.get("type") == "enum":
            pick = next((value for value in spec.get("choices", ()) if value != default), None)
        else:
            low, high = spec.get("min"), spec.get("max")
            pick = low if low is not None and low != default else high
        if pick is not None and pick != default:
            sample = f"{key}={_format_state(pick)}"
            break
    return [base, f"{base}[{sample}]"]


def _state_probes(role_id: int) -> list[dict]:
    """默认状态加单个布尔/模式切换；层数不逐层枚举，也不造状态组合。"""
    specs = teammate_states(role_id)
    defaults = {key: spec.get("default") for key, spec in specs.items()}
    probes = [defaults]
    for key, spec in specs.items():
        choices = (False, True) if spec.get("type") == "bool" else spec.get("choices", ()) if spec.get("type") == "enum" else ()
        for value in choices:
            if value != defaults[key]:
                probes.append({**defaults, key: value})
    return probes


def _effect_state_hint(hits: set[int], probes: list[dict]) -> str:
    # 状态切换均能生效的行不用重复写默认状态；只写确实限制效果的键。
    parts = []
    for key in probes[0]:
        all_values = {probe[key] for probe in probes}
        values = {probes[index][key] for index in hits}
        if values != all_values:
            parts.append(f"{key}=" + "/".join(_format_state(value) for value in sorted(values, key=str)))
    return "；".join(parts)


_CHAIN_PROBES = (0, 1, 2, 3, 4, 5, 6)


_ENV_LABELS: dict[str, str] | None = None


_ENV_PROBES: tuple[dict[str, bool], ...] | None = None


_ATTR_PROBES: tuple[str, ...] | None = None


def _attr_probes() -> tuple[str, ...]:
    """可作为主C的属性。0 是物理，目前没有可选角色。"""
    global _ATTR_PROBES
    if _ATTR_PROBES is None:
        from ..resource.constant import ATTRIBUTE_ID_MAP

        _ATTR_PROBES = tuple(name for attr_id, name in sorted(ATTRIBUTE_ID_MAP.items()) if attr_id)
    return _ATTR_PROBES


def _env_labels() -> dict[str, str]:
    """环境位 -> 中文名，直接读 set_env_* 的文档字符串。"""
    global _ENV_LABELS
    if _ENV_LABELS is None:
        from .damage import DamageAttribute

        _ENV_LABELS = {}
        for name in dir(DamageAttribute):
            if not name.startswith("set_env_"):
                continue
            doc = (getattr(DamageAttribute, name).__doc__ or "").strip()
            if doc:
                _ENV_LABELS[name[len("set_") :]] = doc
        # 协同伤害不是异常效应，但需要说明图单独探测，不能作用于普通伤害。
        _ENV_LABELS["sync_strike"] = "协同攻击"
    return _ENV_LABELS


def _env_probes() -> tuple[dict[str, bool], ...]:
    """每个基础效应探两档：只开效应 / 效应+伤害加深。

    加深档一定带上基础效应，否则会造出「加深开着、效应没开」的假状态。
    """
    global _ENV_PROBES
    if _ENV_PROBES is None:
        labels = _env_labels()
        probes: list[dict[str, bool]] = [{}]
        for flag in labels:
            base = flag[: -len("_deepen")] if flag.endswith("_deepen") else flag
            candidate = {base: True}
            if candidate not in probes:
                probes.append(candidate.copy())
            if f"{base}_deepen" in labels:
                candidate[f"{base}_deepen"] = True
            if candidate not in probes:
                probes.append(candidate)
        _ENV_PROBES = tuple(probes)
    return _ENV_PROBES


def _damage_probes() -> list[tuple[str, str]]:
    """探测用的伤害类型 -> 中文名，取自 utils/damage/utils.py 的 damage_name_map。"""
    from .utils import damage_name_map

    return list(damage_name_map.items())


def _scratch_attr(damage_type: str, char_attr: str, extra: dict, template: str = temp_atk, role_id: int | None = None):
    from .damage import DamageAttribute

    attr = DamageAttribute(char_template=template, char_damage=damage_type, char_attr=char_attr)
    if role_id is not None:
        from types import SimpleNamespace

        attr.role = SimpleNamespace(role=SimpleNamespace(roleId=role_id))
    for key, value in extra.items():
        setattr(attr, key, value)
    return attr
