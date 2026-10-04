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
#   - 每条增益的生效条件  -> 所有对象按实际条件分支划分输入等价类
#   - 可调状态            -> 直接读 Char_xxxx.teammate_states 声明


# 探测用的两个轴都取自现有配置，不手写：
#   主C属性  -> utils/resource/constant.py 的 ATTRIBUTE_ID_MAP
#   环境状态 -> DamageAttribute 上 set_env_* 的文档字符串（"光噪效应" 之类）


def _probe_domains(role_id: int):
    """输入域取现有配置；环境按有效状态成组，数值状态覆盖边界。"""
    domains = {
        "damage": tuple(key for key, _ in _damage_probes()),
        "attribute": _attr_probes(),
        "template": tuple(_TEMPLATE_LABELS),
        "chain": _CHAIN_PROBES,
    }
    fields = {
        "char_damage": ("damage", None),
        "char_attr": ("attribute", None),
        "char_template": ("template", None),
    }
    labels = _env_labels()
    bases = {key.removesuffix("_deepen") for key in labels}
    # 这两个环境由 setter 互相清除，不生成同时开启的假上下文。
    exclusive = {"env_tune_strain", "env_tune_rupture"}
    if exclusive <= bases:
        domains["environment:interference"] = ((), *((key,) for key in sorted(exclusive)))
        for flag in sorted(exclusive):
            fields[flag] = ("environment:interference", lambda flags, flag=flag: flag in flags)
        bases -= exclusive
    for base in sorted(bases):
        axis = f"environment:{base}"
        deepen = f"{base}_deepen"
        domains[axis] = ((), (base,), (base, deepen)) if deepen in labels else ((), (base,))
        for flag in (base, deepen) if deepen in labels else (base,):
            fields[flag] = (axis, lambda flags, flag=flag: flag in flags)
    states = {}
    for key, spec in teammate_states(role_id).items():
        axis = f"state:{key}"
        domains[axis] = _state_values(spec)
        states[key] = (axis, None)
    return domains, fields, states


def _state_values(spec: dict) -> tuple:
    """布尔/枚举与小整数完整覆盖；较大数值范围取默认值和端点。"""
    default = spec.get("default")
    if spec.get("type") == "bool":
        choices = (False, True)
    elif spec.get("type") == "enum":
        choices = tuple(spec.get("choices", ()))
    else:
        low, high = spec.get("min"), spec.get("max")
        if isinstance(low, int) and isinstance(high, int) and 0 <= high - low <= 20:
            choices = tuple(range(low, high + 1))
        else:
            choices = tuple(value for value in (low, high) if value is not None)
    return tuple(dict.fromkeys((default, *choices)))


def _probe_teammate(role_id: int, char_clz: type):
    """所有队友共用实际分支驱动探测，不按角色/装备维护特例计划。"""
    from .probe import ProbeValue, partition_probes

    domains, fields, state_fields = _probe_domains(role_id)
    targets = getattr(char_clz, "teammate_targets", ())
    probe_role_id = targets[0] if targets else None
    effects = {}
    seen_category = set()

    def execute(region):
        attr = _scratch_attr(domains["damage"][0], domains["attribute"][0], {}, domains["template"][0], probe_role_id)
        attr.add_teammate(role_id)
        attr.group_mode = True
        for field, (axis, project) in fields.items():
            setattr(attr, field, ProbeValue(region, axis, project) if project else ProbeValue(region, axis))
        states = {
            key: ProbeValue(region, axis, project) if project else ProbeValue(region, axis)
            for key, (axis, project) in state_fields.items()
        }
        member = TeamMember(role_id=role_id, chain=ProbeValue(region, "chain"), states=states, weapon=False, name=char_clz.name)
        capture = {}
        # 整条真实调用链保留：上游角色/延奏设置环境后再解析条件装备。
        _apply_member(attr, member, capture)
        start = len(attr.effect)
        char_clz()._do_weapon(attr, chain=member.chain, resonLevel=member.reson_level, isGroup=True, states=states)
        capture["weapon"] = [(effect.element_msg, effect.element_value) for effect in attr.effect[start:]]
        return capture

    for region, capture in partition_probes(domains, execute):
        for source, entries in capture.items():
            category = "character" if source == "weapon" else source
            for title, msg in set(entries):
                if not title:
                    continue
                seen_category.add(category)
                info = effects.setdefault(
                    (category, title, msg, source),
                    {"chains": set(), "regions": [], "domains": domains},
                )
                info["chains"].update(region["chain"])
                info["regions"].append(region)
    return effects, seen_category


def detect_teammate(role_id: int) -> dict:
    """空跑探测一名队友实际提供什么、在什么条件下提供。"""
    from .abstract import WavesCharRegister

    role_id = int(role_id)
    char_clz = WavesCharRegister.find_class(role_id)
    if char_clz is None:
        raise TeamConfigError(f"未找到角色【{role_id}】")
    if role_id not in supported_teammate_ids():
        raise TeamConfigError(f"【{getattr(char_clz, 'name', role_id)}】暂不支持作为自定义队友")

    effects, seen_category = _probe_teammate(role_id, char_clz)

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
        effect_state_hint, condition = _effect_hints(info)
        categories[category]["effects"].append(
            {
                "title": title,
                "msg": msg,
                "min_chain": min(info["chains"]),
                "chains": sorted(info["chains"]),
                "source": source,
                "state_hint": effect_state_hint,
                "condition": condition,
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


def _merge_regions(regions: list[dict], keys: tuple[str, ...]) -> set[tuple]:
    """只合并其他轴相同的矩形，不丢失状态、环境与链数的搭配关系。"""
    cubes = {tuple(frozenset(region[key]) for key in keys) for region in regions}
    while True:
        before = len(cubes)
        for axis in range(len(keys)):
            groups = {}
            for cube in cubes:
                key = cube[:axis] + cube[axis + 1 :]
                groups.setdefault(key, set()).update(cube[axis])
            cubes = {key[:axis] + (frozenset(values),) + key[axis:] for key, values in groups.items()}
        if len(cubes) == before:
            return cubes


def _environment_condition(values: frozenset, domain: tuple) -> str:
    """保留环境的开启与关闭约束，以及加深依赖基础效应的合法关系。"""
    choices = [set(value) for value in values]
    flags = set().union(*domain)
    enabled = set.intersection(*choices)
    disabled = flags - set.union(*choices)
    represented = {value for value in domain if enabled <= set(value) and not disabled.intersection(value)}
    if represented != set(values):
        return "/".join("且".join(_env_labels().get(flag, flag) for flag in value) or "无对应环境" for value in sorted(values))
    parts = [_env_labels().get(flag, flag) for flag in sorted(enabled) if f"{flag}_deepen" not in enabled]
    parts.extend(
        "非" + _env_labels().get(flag, flag)
        for flag in sorted(disabled)
        if flag.removesuffix("_deepen") not in disabled or not flag.endswith("_deepen")
    )
    return "且".join(parts)


def _effect_hints(info: dict) -> tuple[str, str]:
    domains = info["domains"]
    keys = tuple(domains)
    cubes = _merge_regions(info["regions"], keys)
    damage_labels = dict(_damage_probes())
    clauses = []
    for cube in sorted(cubes, key=lambda cube: tuple(tuple(sorted(map(str, values))) for values in cube)):
        states, contexts = [], []
        for axis, values in zip(keys, cube):
            if values == set(domains[axis]):
                continue
            if axis.startswith("state:"):
                states.append(
                    axis.removeprefix("state:") + "=" + "/".join(_format_state(value) for value in sorted(values, key=str))
                )
            elif axis.startswith("environment:"):
                contexts.append(_environment_condition(values, domains[axis]))
            elif axis == "chain":
                # 全局链数范围由说明图单独标注，只有分支关联才需再次写链条件。
                if values != info["chains"] or values != set(range(min(values), max(values) + 1)):
                    contexts.append("队友共鸣链=" + "/".join(str(value) for value in sorted(values)))
            elif axis == "damage":
                contexts.append("主角色" + "/".join(damage_labels[value] for value in sorted(values)))
            elif axis == "attribute":
                contexts.append("主角色属性" + "/".join(sorted(values)))
            elif axis == "template":
                contexts.append("主角色模板" + "/".join(_TEMPLATE_LABELS[value] for value in sorted(values)))
        clauses.append(("；".join(states), "；".join(contexts)))
    if len(clauses) == 1:
        return clauses[0]
    return "", " 或 ".join("(" + "；".join(filter(None, clause)) + ")" for clause in clauses)


_CHAIN_PROBES = (0, 1, 2, 3, 4, 5, 6)


_ENV_LABELS: dict[str, str] | None = None


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
