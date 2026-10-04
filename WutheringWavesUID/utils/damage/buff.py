"""队友增益：配置、装备目录、施加逻辑。

- 指令侧：解析「换队友」后把配队挂到 attr（``attr.set_teammate``）
- 计算侧：伤害函数在合适位置调一次 ``attr.set_teammate_buff()``
- 装备目录：从套装 / 声骸 / 武器注册类的 do_teammate 自动生成，不重复维护数值表
- 角色侧：默认用什么装备、能调什么状态，写在 register_char.py 的
  ``teammate_equip`` / ``teammate_states`` 声明里
"""

from dataclasses import dataclass, field
from typing import Any

SONATA_MARK = "合鸣效果-"
ECHO_MARK = "声骸技能-"

KIND_SONATA = "sonata"
KIND_ECHO = "echo"
KIND_WEAPON = "weapon"

KIND_LABELS = {
    KIND_SONATA: "合鸣效果",
    KIND_ECHO: "声骸技能",
    KIND_WEAPON: "专武",
}

KIND_MARKS = {
    KIND_SONATA: SONATA_MARK,
    KIND_ECHO: ECHO_MARK,
}

OFF_VALUES = {"关", "无", "不带", "none", "off", "0"}
DEFAULT_VALUES = {"默认", "default", "开", "1"}

# 条件套：顶层写默认，``cases`` 里按顺序取第一个所有条件都命中的，只覆盖它写了的键
CASES_KEY = "cases"

CASE_ENV = "env"
CASE_DAMAGE = "damage"
CASE_TEMPLATE = "template"
CASE_CHAIN = "chain"

CASE_KEYS = (CASE_ENV, CASE_DAMAGE, CASE_TEMPLATE, CASE_CHAIN)

# 走目录施加的两类；顺序固定，不能用 set（后加的先算会改浮点求和结果）
EQUIP_KINDS = (KIND_SONATA, KIND_ECHO)
# 条件套能覆盖的键：合鸣 / 声骸 / 专武
CASE_EQUIP_KEYS = (*EQUIP_KINDS, KIND_WEAPON)


def _preset_classes(kind: str) -> dict[str, type]:
    """注册类覆盖 do_teammate 就进入目录；不另维护装备名单。"""
    from .abstract import EchoAbstract, SonataAbstract, WavesEchoRegister, WavesSonataRegister

    if kind == KIND_SONATA:
        from .register_sonata import register_sonata

        registry, base, register = WavesSonataRegister, SonataAbstract, register_sonata
    elif kind == KIND_ECHO:
        from .register_echo import register_echo

        registry, base, register = WavesEchoRegister, EchoAbstract, register_echo
    else:
        return {}
    if not registry._id_cls_map:
        register()
    return {
        clz.name.removeprefix("共鸣回响·"): clz
        for clz in registry._id_cls_map.values()
        if clz.name and clz.do_teammate is not base.do_teammate
    }


def preset_of(kind: str, key: str) -> type | None:
    return _preset_classes(kind).get(key.removeprefix("共鸣回响·"))


def preset_names(kind: str) -> list[str]:
    return list(_preset_classes(kind))


def apply_preset(attr, char_name: str, kind: str, key: str) -> bool:
    """调用装备注册类的队友增益，不施加持有者自身效果。"""
    clz = preset_of(kind, key)
    if clz is None:
        return False
    clz().do_teammate(attr, char_name)
    return True


def apply_declared_equip(attr, char_name: str, declared: dict) -> None:
    """把角色声明里的默认合鸣 / 声骸按目录加上去。

    生效条件与数值由装备注册类的 do_teammate 统一维护。
    角色没声明的那一类直接跳过，用户覆盖由调用方处理。
    """
    for kind in EQUIP_KINDS:
        key = declared.get(kind)
        if key:
            apply_preset(attr, char_name, kind, key)


def declared_cases(declared: dict) -> tuple[dict, ...]:
    """角色声明的条件套（``teammate_equip["cases"]``），顺便挡住写错的键。

    条件套是「满足条件时改带另一套」：顶层还是默认，命中哪套就换哪套。
    键写错会静默变成「永远命中」，所以这里直接报错而不是忽略。
    """
    cases = declared.get(CASES_KEY) or ()
    if isinstance(cases, dict):
        raise TeamConfigError(f"队友装备的【{CASES_KEY}】要写成列表，每一项是一套条件装备")
    result: list[dict] = []
    for case in cases:
        if not isinstance(case, dict):
            raise TeamConfigError(f"队友装备的【{CASES_KEY}】里每一项都要是 {{条件…, 合鸣…, 声骸…}}")
        for key in case:
            if key not in CASE_KEYS and key not in CASE_EQUIP_KEYS:
                raise TeamConfigError(f"队友装备的条件套里不认识的键【{key}】")
        result.append(dict(case))
    return tuple(result)


def case_matches(attr, case: dict, chain: int = 0) -> bool:
    """条件套是否命中：写了的条件之间是 AND，一个都不写就是无条件命中。

    - ``env``      主角色身上的环境位为真（例如 ``env_fusion_burst``）
    - ``damage``   主角色当前的伤害类型（``attr.char_damage``）
    - ``template`` 主角色的模板（``attr.char_template``）
    - ``chain``    队友自己的共鸣链下限
    """
    env = case.get(CASE_ENV)
    if env and not getattr(attr, env, False):
        return False
    damage = case.get(CASE_DAMAGE)
    if damage and attr.char_damage != damage:
        return False
    template = case.get(CASE_TEMPLATE)
    if template and attr.char_template != template:
        return False
    need_chain = case.get(CASE_CHAIN)
    return need_chain is None or int(chain) >= int(need_chain)


def match_case(attr, declared: dict, chain: int = 0) -> dict | None:
    """按顺序取第一个所有条件都命中的条件套，没有命中的返回 None。"""
    for case in declared_cases(declared):
        if case_matches(attr, case, chain):
            return case
    return None


def resolve_declared_equip(attr, declared: dict, chain: int = 0) -> dict:
    """解析这次实际要带的装备：顶层默认 + 命中的条件套覆盖写了的键。

    只读 attr 上当时的状态和队友自己的共鸣链，不写任何数值；施加还是走目录。
    """
    equip = {kind: declared.get(kind) for kind in CASE_EQUIP_KEYS}
    case = match_case(attr, declared, chain)
    if case:
        for kind in CASE_EQUIP_KEYS:
            if case.get(kind):
                equip[kind] = case[kind]
    return equip


def _weapon_classes() -> dict[int, type]:
    from .abstract import WavesWeaponRegister, WeaponAbstract
    from .register_weapon import register_weapon

    if not WavesWeaponRegister._id_cls_map:
        register_weapon()
    return {
        weapon_id: clz
        for weapon_id, clz in WavesWeaponRegister._id_cls_map.items()
        if clz.do_teammate is not WeaponAbstract.do_teammate
    }


def weapon_name(weapon_id: int | None) -> str | None:
    if not weapon_id:
        return None
    from .abstract import WavesWeaponRegister

    clz = WavesWeaponRegister.find_class(int(weapon_id))
    return clz.name if clz else None


def weapon_options() -> list[tuple[int, str]]:
    """可选武器自动取自覆盖队友方法的注册类。"""
    return sorted(((weapon_id, clz.name) for weapon_id, clz in _weapon_classes().items()), key=lambda item: item[1])


def resolve_weapon_id(value: Any) -> int | None:
    text = str(value).strip()
    if text.isdigit():
        candidate = int(text)
        return candidate if candidate in _weapon_classes() else None
    return next((weapon_id for weapon_id, name in weapon_options() if name == text), None)


def apply_weapon(attr, weapon_id: int, reson_level: int, is_group: bool, char_name: str = "") -> bool:
    """默认武器与替换武器走同一注册入口，行为不再由角色或目录重复声明。"""
    clz = _weapon_classes().get(int(weapon_id))
    if clz is None:
        return False
    clz(int(weapon_id), 90, 6, reson_level).do_teammate(attr, char_name, is_group)
    return True


CATEGORY_CHARACTER = "character"
CATEGORY_OUTRO = "outro"
CATEGORY_SONATA = "sonata"
CATEGORY_ECHO = "echo"

ALL_CATEGORIES = (CATEGORY_CHARACTER, CATEGORY_OUTRO, CATEGORY_SONATA, CATEGORY_ECHO)

CATEGORY_LABELS: dict[str, str] = {
    CATEGORY_CHARACTER: "角色自身增益",
    CATEGORY_OUTRO: "延奏技能",
    CATEGORY_SONATA: "合鸣效果",
    CATEGORY_ECHO: "声骸技能",
}


SONATA_MARK = "合鸣效果-"
ECHO_MARK = "声骸技能-"

# 合鸣/声骸/武器的两种特殊取值
EQ_DEFAULT = "default"
EQ_NONE = "none"

_MAX_MEMBERS = 2


class TeamConfigError(ValueError):
    """自定义配队配置错误（面向用户的提示信息）。"""


@dataclass
class TeamMember:
    """一名自定义队友的配置。"""

    role_id: int
    chain: int = 0
    reson_level: int = 1
    # 总开关：关闭后该队友不提供任何增益
    character_buff: bool = True
    # 分类开关
    outro: bool = True
    # "default" 用角色声明里的默认 | "none" 关 | 其它值为替换的预设名
    sonata: str = EQ_DEFAULT
    echo: str = EQ_DEFAULT
    # 是否计算专武
    weapon: bool = True
    # 指定武器（id），None 表示用声明里的默认
    weapon_id: int | None = None
    # 角色特有状态覆盖，默认值由各角色 _do_buff 决定
    states: dict[str, Any] = field(default_factory=dict)
    # validate_team 后填充，用于展示
    name: str = ""

    def describe(self) -> str:
        if self.weapon_id:
            weapon_text = f"武器={weapon_name(self.weapon_id) or self.weapon_id}"
        elif self.weapon:
            weapon_text = f"专武精{self.reson_level}"
        else:
            weapon_text = "不计专武"
        parts = [f"{self.chain}链", weapon_text]
        if not self.character_buff:
            parts.append("无增益")
            return "·".join(parts)
        if not self.outro:
            parts.append("无延奏")
        if self.sonata == EQ_NONE:
            parts.append("无合鸣")
        elif self.sonata != EQ_DEFAULT:
            parts.append(f"合鸣={self.sonata}")
        if self.echo == EQ_NONE:
            parts.append("无声骸")
        elif self.echo != EQ_DEFAULT:
            parts.append(f"声骸={self.echo}")
        for key, value in self.states.items():
            parts.append(f"{key}={_format_state(value)}")
        return "·".join(parts)


def _format_state(value: Any) -> str:
    if isinstance(value, bool):
        return "开" if value else "关"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _char_registry():
    from .abstract import WavesCharRegister

    return WavesCharRegister


def teammate_states(role_id: int) -> dict[str, dict]:
    """某角色声明的「可调状态」，来源是 Char_xxxx.teammate_states。"""
    char_clz = _char_registry().find_class(int(role_id))
    if char_clz is None:
        return {}
    declared = getattr(char_clz, "teammate_states", None)
    if not isinstance(declared, dict):
        return {}
    return {key: dict(spec) for key, spec in declared.items()}


def teammate_equip(role_id: int) -> dict:
    """某角色声明的默认装备，来源是 Char_xxxx.teammate_equip。

    只声明角色真正写死过的东西：没写武器就没有 ``weapon`` 键。
    """
    char_clz = _char_registry().find_class(int(role_id))
    if char_clz is None:
        return {}
    declared = getattr(char_clz, "teammate_equip", None)
    return dict(declared) if isinstance(declared, dict) else {}


def state_spec(role_id: int, key: str) -> dict | None:
    return teammate_states(role_id).get(key)


def state_default(role_id: int, key: str) -> Any:
    spec = state_spec(role_id, key)
    if not spec:
        return None
    return spec.get("default")


def state_hint(role_id: int, key: str) -> str:
    """把声明渲染成一行人类可读的范围说明，例如 "0~10，默认10"。"""
    spec = state_spec(role_id, key)
    if not spec:
        return ""
    kind = spec.get("type", "int")
    default = spec.get("default")
    if kind == "bool":
        return f"开/关，默认{'开' if default is not False else '关'}"
    if kind == "enum":
        choices = "、".join(spec.get("choices", ()))
        return f"{choices}，默认{default}"
    low, high = spec.get("min"), spec.get("max")
    span = f"{_format_state(low)}~{_format_state(high)}" if low is not None and high is not None else "数值"
    return f"{span}，默认{_format_state(default)}"


def supported_teammate_ids() -> set[int]:
    """角色、延奏、武器或装备任一提供队友增益，都允许配置。"""
    from .abstract import CharAbstract

    result: set[int] = set()
    for role_id, char_clz in _char_registry()._id_cls_map.items():
        methods = ("_do_buff", "_do_outro", "_do_weapon")
        if any(getattr(char_clz, name) is not getattr(CharAbstract, name) for name in methods) or getattr(
            char_clz, "teammate_equip", None
        ):
            result.add(int(role_id))
    return result


def char_name(role_id: int) -> str:
    char_clz = _char_registry().find_class(role_id)
    if char_clz is None:
        return str(role_id)
    return char_clz.name or str(role_id)


def is_registered(role_id: int) -> bool:
    """该角色是否已经在注册表里（注册表在 bot 启动时才填充）。"""
    try:
        return _char_registry().find_class(int(role_id)) is not None
    except (TypeError, ValueError):
        return False


def coerce_state(role_id: int, key: str, value: Any) -> Any:
    """把用户输入的状态值转成规范形式；不合法或该角色没声明时抛 TeamConfigError。"""
    spec = state_spec(role_id, key)
    if spec is None:
        raise TeamConfigError(f"该队友不支持状态【{key}】")
    return _check_state(char_name(role_id), key, spec, value)


def validate_team(members: Any, main_role_id: int | None = None) -> tuple[TeamMember, ...]:
    """校验并补全队友配置，非法配置抛出 TeamConfigError。"""
    if members is None:
        raise TeamConfigError("没有需要校验的队友配置")

    members = tuple(members)
    if not members:
        raise TeamConfigError("请至少填写1名队友")
    if len(members) > _MAX_MEMBERS:
        raise TeamConfigError(f"自定义配队最多支持{_MAX_MEMBERS}名队友")

    supported = supported_teammate_ids()
    seen: set[int] = set()
    result: list[TeamMember] = []
    for member in members:
        role_id = int(member.role_id)
        name = char_name(role_id)
        chain = int(getattr(member, "chain", 0) or 0)
        reson_level = int(getattr(member, "reson_level", 1) or 1)
        sonata = getattr(member, "sonata", EQ_DEFAULT) or EQ_DEFAULT
        echo = getattr(member, "echo", EQ_DEFAULT) or EQ_DEFAULT
        if role_id in seen:
            raise TeamConfigError(f"队友【{name}】重复")
        if main_role_id is not None and role_id == int(main_role_id):
            raise TeamConfigError(f"队友【{name}】不能是当前计算伤害的角色本身")
        if role_id not in supported:
            raise TeamConfigError(f"【{name}】暂不支持作为自定义队友（没有可用的辅助增益模型）")
        if not 0 <= chain <= 6:
            raise TeamConfigError(f"队友【{name}】共鸣链范围是0至6")
        if not 1 <= reson_level <= 5:
            raise TeamConfigError(f"队友【{name}】武器精炼范围是1至5")

        declared = teammate_equip(role_id)
        sonata = _check_equip_choice(name, "合鸣", KIND_SONATA, sonata)
        echo = _check_equip_choice(name, "声骸", KIND_ECHO, echo)

        weapon_id = getattr(member, "weapon_id", None)
        if weapon_id:
            resolved = resolve_weapon_id(weapon_id)
            if resolved is None:
                options = "、".join(name for _id, name in weapon_options())
                raise TeamConfigError(f"队友【{name}】找不到能用的武器【{weapon_id}】，可填：{options}，或填 关")
            weapon_id = resolved
        else:
            weapon_id = None

        states = dict(getattr(member, "states", None) or {})
        allowed = teammate_states(role_id)
        for key, value in states.items():
            if key not in allowed:
                if allowed:
                    raise TeamConfigError(f"队友【{name}】不支持状态【{key}】，可用：{'、'.join(allowed)}")
                raise TeamConfigError(f"队友【{name}】不支持任何状态设置")
            states[key] = _check_state(name, key, allowed[key], value)

        seen.add(role_id)
        result.append(
            TeamMember(
                role_id=role_id,
                chain=chain,
                reson_level=reson_level,
                character_buff=bool(getattr(member, "character_buff", True)),
                outro=bool(getattr(member, "outro", True)),
                sonata=sonata,
                echo=echo,
                weapon=bool(getattr(member, "weapon", True)),
                weapon_id=weapon_id,
                states=states,
                name=name,
            )
        )
    return tuple(result)


def _check_equip_choice(name: str, label: str, kind: str, choice: str) -> str:
    """合鸣/声骸的取值：default / none / 目录里存在的预设名。"""
    if choice in (EQ_DEFAULT, EQ_NONE):
        return choice
    if choice not in preset_names(kind):
        raise TeamConfigError(
            f"队友【{name}】的{label}【{choice}】不在可用列表里，可填：{'、'.join(preset_names(kind))}，或填 关"
        )
    return choice


def _check_state(name: str, key: str, spec: dict, value: Any) -> Any:
    """按角色自己声明的状态规格校验取值。"""
    kind = spec.get("type", "int")

    if kind == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value > 0
        if isinstance(value, str):
            return value.strip().casefold() in ("开", "是", "true", "1")
        raise TeamConfigError(f"队友【{name}】的【{key}】只能填写开/关")

    if kind == "enum":
        choices = tuple(spec.get("choices", ()))
        if value not in choices:
            raise TeamConfigError(f"队友【{name}】的【{key}】只能是{'/'.join(choices)}")
        return value

    low, high = spec.get("min"), spec.get("max")
    try:
        number = float(value)
    except (TypeError, ValueError) as e:
        raise TeamConfigError(f"队友【{name}】的【{key}】需要填写数字") from e
    if number != number or number in (float("inf"), float("-inf")):
        raise TeamConfigError(f"队友【{name}】的【{key}】不是合法数值")
    if low is not None and number < low:
        raise TeamConfigError(f"队友【{name}】的【{key}】不能小于{_format_state(low)}")
    if high is not None and number > high:
        raise TeamConfigError(f"队友【{name}】的【{key}】不能大于{_format_state(high)}")
    return int(number) if number.is_integer() else number


def describe_team(members: tuple[TeamMember, ...] | None) -> list[str]:
    """把配队配置拆成适合逐行展示的文本。"""
    if not members:
        return ["自定义配队：无"]
    rows = ["自定义配队（仅本次模拟，不参与排名）"]
    for index, member in enumerate(members, start=1):
        rows.append(f"队友{index}：{member.name}　{member.describe()}")
    return rows


def _record_effects(attr, start: int, category: str, capture: dict | None) -> None:
    if capture is not None:
        capture.setdefault(category, []).extend((effect.element_msg, effect.element_value) for effect in attr.effect[start:])


def _apply_member(attr, member: TeamMember, captured: dict | None = None, isGroup: bool = True) -> None:
    """角色增益 -> 延奏 -> 合鸣 -> 声骸 -> 武器，每段只执行一次。

    captured 仅供说明图/副本探测记录新增效果，不改变任何方法或注册表。
    """
    if not member.character_buff:
        return
    char_clz = _char_registry().find_class(member.role_id)
    if char_clz is None:
        raise TeamConfigError(f"未找到角色【{member.role_id}】")
    char = char_clz()
    kwargs = {"chain": member.chain, "resonLevel": member.reson_level, "isGroup": isGroup, "states": dict(member.states)}

    start = len(attr.effect)
    char._do_buff(attr, **kwargs)
    _record_effects(attr, start, CATEGORY_CHARACTER, captured)

    if member.outro:
        start = len(attr.effect)
        char._do_outro(attr, **kwargs)
        _record_effects(attr, start, CATEGORY_OUTRO, captured)

    # 角色与延奏先设置环境，条件装备随后解析；不需要先试加再补加。
    equipped = resolve_declared_equip(attr, teammate_equip(member.role_id), member.chain)
    for kind, chosen in ((KIND_SONATA, member.sonata), (KIND_ECHO, member.echo)):
        if chosen == EQ_NONE:
            continue
        key = equipped.get(kind) if chosen == EQ_DEFAULT else chosen
        if key:
            start = len(attr.effect)
            apply_preset(attr, member.name or char.name, kind, key)
            _record_effects(attr, start, kind, captured)

    if member.weapon:
        start = len(attr.effect)
        if member.weapon_id:
            if not apply_weapon(attr, member.weapon_id, member.reson_level, isGroup, member.name or char.name):
                raise TeamConfigError(f"【{member.name}】无法触发该武器，请换回默认或填 关")
        else:
            char._do_weapon(attr, **kwargs)
        _record_effects(attr, start, CATEGORY_CHARACTER, captured)


def default_member(spec) -> TeamMember:
    """把 ``(角色id, 共鸣链, 精炼)`` 这种简写变成 TeamMember。"""
    role_id, chain, reson_level = spec
    return TeamMember(role_id=int(role_id), chain=int(chain), reson_level=int(reson_level))


def apply_teammates(attr) -> None:
    """应用队友增益。伤害函数通过 ``attr.set_teammate_buff()`` 调到这里。

    一次计算只应用一次：条目可能在不同层级各调一次，重复应用会叠加。
    """
    if getattr(attr, "_teammate_applied", False):
        return
    members = getattr(attr, "_teammate_config", None) or ()
    members = tuple(m if isinstance(m, TeamMember) else default_member(m) for m in members)
    if not members:
        return

    members = _fill_names(members)
    attr.group_mode = True
    for member in members:
        attr.add_teammate(member.role_id)
    for member in members:
        _apply_member(attr, member)
    attr._teammate_applied = True


def _fill_names(members: tuple[TeamMember, ...]) -> tuple[TeamMember, ...]:
    """补上角色名，展示和报错都要用。"""
    filled = []
    for member in members:
        if not member.name:
            member = TeamMember(**{**member.__dict__, "name": char_name(member.role_id)})
        filled.append(member)
    return tuple(filled)


def attach_teammate(attr, members) -> None:
    """挂队友配置：换队友或条目自带的默认配队。

    先挂的生效，所以用户换队友时条目里的默认配队不会顶掉它。
    配队说明在这里写一次（聚合型伤害函数会把 attr 复制几份，写在这里才不会重复）。
    """
    if getattr(attr, "_teammate_config", None):
        return
    # 兼容三种写法：一组 TeamMember、单个 (id, 链, 精炼)、多个 (id, 链, 精炼)
    if len(members) == 1 and isinstance(members[0], (list, tuple)):
        first = members[0][0] if members[0] else None
        if isinstance(first, (TeamMember, list, tuple)):
            members = tuple(members[0])
    config = tuple(m if isinstance(m, TeamMember) else default_member(m) for m in members)
    attr._teammate_config = config
    add_team_rows(attr, _fill_names(config))


def add_team_rows(attr, members: tuple[TeamMember, ...]) -> None:
    """列出这次上了谁：队友1·莫宁 / 0链·专武精1（后面跟自定义的状态、装备等）。

    ``_teammate_rows_added`` 是给聚合型伤害函数用的：它们会把 attr 复制几份分别算，
    没有这个标记同一段说明会被拼进来好几次。
    """
    if getattr(attr, "_teammate_rows_added", False):
        return
    attr._teammate_rows_added = True
    for index, member in enumerate(members, start=1):
        attr.add_effect(f"队友{index}·{member.name}", member.describe())


def _has_config(attr) -> bool:
    return getattr(attr, "_teammate_config", None) is not None
