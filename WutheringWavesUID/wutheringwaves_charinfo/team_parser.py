"""解析「换队友」指令段。

语法（可与现有的 换角色/换武器/换声骸/换合鸣/换敌人 段混用）::

    心伤害3 换队友 散华61 守岸人01
    心伤害3 换队友 散华6链专武精一 守岸人01[领域=开,延奏=开,合鸣=关]

- 队友之间可用空格分隔或直接连写（如 ``换队友守岸人01散华``），最多两人；
- 队友名字支持角色别名，名字后面可以跟 ``61``（6链、专武精1）、
  ``6链专武精一``、``6链``、``精3`` 等写法，不写则默认 0链 精1；
- 两位简写的精炼位 ``0`` 表示不计专武（``00`` 为0链，``60`` 为6链），
  单独 ``0`` 等同 ``00``；方括号内显式武器配置优先于简写；
- ``[]`` 内是该队友的状态配置，可用逗号、空格、分号或顿号分隔，可写：
  角色增益 / 延奏 / 武器 / 合鸣 / 声骸 = 开|关，
  以及角色特有状态（领域、祝福层数、暴击增益、固定攻击、模式）。
"""

import re
from typing import Any

from ..utils.damage.buff import (
    TeamConfigError,
    TeamMember,
    char_name,
    coerce_state,
    is_registered,
    state_spec,
)
from ..utils.name_convert import (
    alias_to_char_name,
    alias_to_echo_name,
    alias_to_sonata_name,
    char_name_to_char_id,
    weapon_name_to_weapon_id,
)

TEAM_PREFIX = "换队友"

_DIGITS = {str(i): i for i in range(10)} | dict(zip("零一二三四五六七八九", range(10)))
_RESON_DIGITS = dict(_DIGITS) | {"满": 5}

_BOOL_VALUES = {
    "开": True,
    "关": False,
    "是": True,
    "否": False,
    "true": True,
    "false": False,
    "1": True,
    "0": False,
}

_SWITCH_VALUES = {"默认": "default", "default": "default", "开": "default", "关": "none", "none": "none"}

DEFAULT_WORDS = {"默认", "default", "开", "1", "是"}
OFF_WORDS = {"关", "无", "不带", "none", "off", "0", "否"}

_SWITCH_KEYS = {
    "角色增益": "character_buff",
    "队友增益": "character_buff",
    "增益": "character_buff",
    "延奏": "outro",
    "延奏技能": "outro",
    "武器": "weapon",
    "专武": "weapon",
    "合鸣": "sonata",
    "合鸣效果": "sonata",
    "套装": "sonata",
    "声骸": "echo",
    "声骸技能": "echo",
}

_STATE_KEYS = {
    "领域": "领域",
    "祝福层数": "祝福层数",
    "层数": "祝福层数",
    "暴击增益": "暴击增益",
    "固定攻击": "固定攻击",
    "模式": "模式",
}

_SUFFIX_RULES = (
    (re.compile(r"^(?P<chain>[0-9零一二三四五六七八九])链专武精(?P<reson>[0-9一二三四五满])$"), True),
    (re.compile(r"^(?P<chain>[0-9零一二三四五六七八九])链精(?P<reson>[0-9一二三四五满])$"), True),
    (re.compile(r"^(?P<chain>[0-9零一二三四五六七八九])链$"), False),
    (re.compile(r"^专武精(?P<reson>[0-9一二三四五满])$"), False),
    (re.compile(r"^精(?P<reson>[0-9一二三四五满])$"), False),
    (re.compile(r"^(?P<chain>[0-9])(?P<reson>[0-9])$"), True),
)


class TeamParseError(ValueError):
    """换队友指令格式错误。"""


def _char_id_of(name: str) -> int | None:
    """名字（含别名）-> 角色 id，直接用 utils/name_convert 里现成的别名表。

    别名里有 ``jkl``、``sp秧秧`` 这种带英文的写法，所以大小写不同时再试一次。
    """
    names = [name]
    if name != name.casefold():
        names.append(name.casefold())
    for text in names:
        role_id = char_name_to_char_id(text)
        if role_id:
            return int(role_id)
    return None


def _split_options(token: str) -> tuple[str, str | None]:
    if "[" not in token:
        return token, None
    name, options = token.split("[", 1)
    if not options.endswith("]"):
        raise TeamParseError("队友状态括号未闭合，请使用 [状态=值] 的形式")
    if "]" in options[:-1]:
        raise TeamParseError("队友状态格式错误，不能嵌套括号")
    return name.strip(), options[:-1]


def _tokenize(body: str) -> list[str]:
    """按空格切分队友；方括号内的空格和逗号都属于状态配置。"""
    # 兼容中文输入法括号，以及名字和状态括号间的空白。
    body = body.translate(str.maketrans("［］【】", "[][]"))
    body = re.sub(r"(?<=\S)\s+(?=\[)", "", body)
    tokens: list[str] = []
    current = ""
    inside = False
    for char in body:
        if char == "[":
            if inside:
                raise TeamParseError("队友状态括号不能嵌套")
            inside = True
        elif char == "]":
            if not inside:
                raise TeamParseError("队友状态括号不匹配")
            inside = False
        if (char.isspace() or char in ",，、") and not inside:
            if current:
                tokens.append(current)
                current = ""
        else:
            current += char
    if inside:
        raise TeamParseError("队友状态括号未闭合")
    if current:
        tokens.append(current)
    return [member for token in tokens for member in _split_packed_members(token)]


def _split_packed_members(token: str) -> list[str]:
    """以现有名字/后缀规则拆连写队友；完整名字优先，不切开状态括号。"""
    boundaries = [0]
    inside = False
    for index, char in enumerate(token, start=1):
        if char == "[":
            inside = True
        elif char == "]":
            inside = False
        if not inside:
            boundaries.append(index)
    cache: dict[int, list[str] | None] = {len(token): []}

    def split(start: int) -> list[str] | None:
        if start in cache:
            return cache[start]
        for end in reversed(boundaries):
            if end <= start:
                continue
            part = token[start:end]
            try:
                name, _ = _split_options(part)
                matched = _match_member(name)
            except TeamParseError:
                continue
            if matched is None:
                continue
            rest = split(end)
            if rest is not None:
                cache[start] = [part, *rest]
                return cache[start]
        cache[start] = None
        return None

    # 拆不出来时仍交给原解析路径报错，不吞掉非法后缀/状态错误。
    return split(0) or [token]


def _match_suffix(rest: str) -> tuple[int, int, bool] | None:
    if rest == "0":
        return 0, 1, False
    for pattern, has_both in _SUFFIX_RULES:
        match = pattern.match(rest)
        if not match:
            continue
        groups = match.groupdict()
        chain = _DIGITS.get(groups["chain"], 0) if groups.get("chain") else 0
        reson = _RESON_DIGITS.get(groups["reson"], 1) if groups.get("reson") else 1
        # 仅数字简写的精炼位0代表无专武，不把非法精炼0传入伤害计算。
        weapon = not (len(rest) == 2 and rest.isdigit() and reson == 0)
        if not weapon:
            reson = 1
        if has_both and (not 0 <= chain <= 6 or not 1 <= reson <= 5):
            raise TeamParseError("共鸣链范围是0至6，武器精炼范围是1至5")
        return chain, reson, weapon
    return None


def _match_member(name_part: str) -> tuple[int, int, int, bool, str] | None:
    """把「名字」或「名字+链/精炼后缀」解析成 ``(角色id, 共鸣链, 精炼, 计专武, 命中名字)``。

    先按整个名字查一次（别名表里认得的就是这个分支），认不出再拆「散华61」
    「尤诺21」「散华6链专武精一」这种后缀：从长名字往短里试，和旧实现
    「按长度从长到短试别名」的顺序一致。名字认不出来返回 None。
    """
    role_id = _char_id_of(name_part)
    if role_id is not None:
        return role_id, 0, 1, True, alias_to_char_name(name_part)

    for index in range(len(name_part) - 1, 0, -1):
        parsed = _match_suffix(name_part[index:])
        if parsed is None:
            continue
        head = name_part[:index]
        head_id = _char_id_of(head)
        if head_id is None:
            continue
        chain, reson, weapon = parsed
        return head_id, chain, reson, weapon, alias_to_char_name(head)
    return None


def _parse_member_token(token: str, member_factory):
    name_part, options_text = _split_options(token)

    matched = _match_member(name_part)
    if matched is None:
        raise TeamParseError(f"未知队友或配置写法【{name_part}】，请检查角色名是否正确")
    role_id, chain, reson, weapon, matched_name = matched

    if not 0 <= chain <= 6:
        raise TeamParseError("共鸣链范围是0至6")
    if not 1 <= reson <= 5:
        raise TeamParseError("武器精炼范围是1至5")

    fields, rows = _parse_options(options_text, role_id)
    if not weapon:
        fields.setdefault("weapon", False)
    member = member_factory(role_id=role_id, chain=chain, reson_level=reson, **fields)
    return member, rows, matched_name


def _parse_options(options_text: str | None, role_id: int):
    fields: dict = {}
    rows: list[tuple[str, str]] = []
    if options_text is None:
        return fields, rows
    if not options_text.strip():
        raise TeamParseError("队友状态不能为空，请删除空的方括号")

    states: dict = {}
    seen: set[str] = set()
    # 只在下一个“名称=值”之前拆空白，保留装备名称/状态值内部的空格；
    # 等号两侧允许空白，连续或末尾分隔符也不影响有效配置。
    option_parts = re.split(r"[,，;；、]+|\s+(?=[^\s=＝:：,，;；、]+\s*[=＝:：])", options_text)
    if not any(raw.strip() for raw in option_parts):
        raise TeamParseError("队友状态不能为空，请填写 名称=值")
    for raw in option_parts:
        if not raw.strip():
            continue
        pair = re.split("[=＝:：]", raw)
        if len(pair) != 2 or not pair[0].strip() or not pair[1].strip():
            raise TeamParseError(f"队友状态【{raw.strip()}】要写成 名称=值 的形式")
        key, value = pair[0].strip(), pair[1].strip()
        target = _SWITCH_KEYS.get(key) or _STATE_KEYS.get(key)
        if target is None and state_spec(role_id, key) is not None:
            target = key
        if target is None:
            raise TeamParseError(f"未知队友状态【{key}】")
        if target in seen:
            raise TeamParseError(f"队友状态【{key}】重复")
        seen.add(target)

        if target in ("character_buff", "outro"):
            fields[target] = _parse_bool(key, value)
        elif target == "weapon":
            # 武器可以填 开/关，也可以直接填武器名或武器id
            folded = value.casefold()
            if folded in _BOOL_VALUES:
                fields["weapon"] = _BOOL_VALUES[folded]
            elif folded in OFF_WORDS:
                fields["weapon"] = False
            else:
                if not value.isdigit():
                    weapon_id = weapon_name_to_weapon_id(value)
                    if weapon_id is None:
                        raise TeamParseError(f"找不到武器【{value}】，请填武器名或武器 ID，或填 开/关")
                    value = weapon_id
                fields["weapon_id"] = value
                fields["weapon"] = True
        elif target in ("sonata", "echo"):
            fields[target] = _parse_equip_choice(value, target)
        else:
            states[target] = _parse_state(role_id, target, key, value)
        rows.append((key, value))

    if states:
        fields["states"] = states
    return fields, rows


def _parse_equip_choice(value: str, kind: str) -> str:
    """合鸣/声骸：默认、关，或者写预设名（支持别名）。

    别名解析出来的是**规范预设名**（对应 PRESETS 里的 key），
    认不出来就原样传给 validate_team，让那边报「不在可用列表里」。
    """
    folded = value.casefold()
    if folded in DEFAULT_WORDS:
        return "default"
    if folded in OFF_WORDS:
        return "none"
    if kind == "sonata":
        return alias_to_sonata_name(value) or value
    if kind == "echo":
        return alias_to_echo_name(value) or value
    return value


def _parse_state(role_id: int, target: str, key: str, value: str):
    """状态值按角色自己声明的规格解析；注册表还没加载时先宽松解析，交给 validate_team 复核。"""
    spec = state_spec(role_id, target)
    if spec is None:
        if is_registered(role_id):
            raise TeamParseError(f"该队友不支持状态【{key}】")
        return _infer_raw(value)

    kind = spec.get("type", "int")
    if kind == "bool":
        raw: Any = _parse_bool(key, value)
    elif kind == "enum":
        raw = value
    else:
        raw = _parse_number(key, value)
    try:
        return coerce_state(role_id, target, raw)
    except TeamConfigError as e:
        raise TeamParseError(str(e)) from e


def _infer_raw(value: str):
    folded = value.casefold()
    if folded in _BOOL_VALUES:
        return _BOOL_VALUES[folded]
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?%?", value):
        return value
    return value


def _parse_bool(key: str, value: str) -> bool:
    result = _BOOL_VALUES.get(value.casefold())
    if result is None:
        raise TeamParseError(f"【{key}】只能填写 开/关")
    return result


def _parse_number(key: str, value: str):
    text = value[:-1] if value.endswith("%") else value
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text):
        raise TeamParseError(f"【{key}】需要填写数字")
    number = float(text)
    return int(number) if number.is_integer() else number


def parse_team_change(
    content: str | None,
    main_role_id: int | None = None,
    member_factory=None,
):
    """从指令文本里解析「换队友」段。

    :return: (队友元组或None, 去掉队友段后的剩余指令, 展示用配置行)
    """
    content = content or ""
    if member_factory is None:
        member_factory = TeamMember

    segments = re.split(r"(?=换)", content)
    teams = [segment for segment in segments if segment.strip().startswith(TEAM_PREFIX)]
    if not teams:
        return None, content, ()
    if len(teams) > 1:
        raise TeamParseError("一次查询只能使用一段「换队友」")

    body = teams[0].strip()[len(TEAM_PREFIX) :]
    tokens = _tokenize(body)
    if not tokens:
        raise TeamParseError("请在「换队友」后面填写队友，例如：换队友 散华61 守岸人01")
    if len(tokens) > 2:
        raise TeamParseError("自定义配队最多支持两名队友")

    members: list = []
    rows: list[tuple[str, str]] = []
    seen: set[int] = set()
    for token in tokens:
        member, member_rows, matched_name = _parse_member_token(token, member_factory)
        role_id = int(member.role_id)
        if role_id in seen:
            raise TeamParseError(f"队友【{token}】重复，不能重复上阵同一角色")
        if main_role_id is not None and role_id == int(main_role_id):
            raise TeamParseError("队友不能是当前计算伤害的主角色本身")
        seen.add(role_id)
        members.append(member)
        # 展示用规范名，避免用户写别名时图里出现「达尼亚」这种非正式写法
        display_name = char_name(role_id) if is_registered(role_id) else matched_name
        rows.append((f"队友{len(members)}·{display_name}", _format_member(member)))
        rows.extend((f"　{display_name}·{key}", value) for key, value in member_rows)

    remaining = "".join(segment for segment in segments if segment is not teams[0]).strip()
    return tuple(members), remaining, tuple(rows)


def _format_member(member) -> str:
    describe = getattr(member, "describe", None)
    if callable(describe):
        return describe()
    parts = [f"{member.chain}链", f"专武精{member.reson_level}"]
    states = getattr(member, "states", None) or {}
    for key, value in states.items():
        parts.append(f"{key}={value}")
    return "·".join(parts)
