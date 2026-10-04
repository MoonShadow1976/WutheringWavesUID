"""队友配置卡片：核心增益优先，装备目录单独查看。"""

from functools import lru_cache
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps

from ..utils.ascension.echo import echo_id_data
from ..utils.ascension.weapon import get_weapon_id
from ..utils.damage.buff import KIND_ECHO, KIND_SONATA, KIND_WEAPON, TeamConfigError, preset_names, weapon_options
from ..utils.damage.team import detect_teammate, example_commands, teammate_overview
from ..utils.fonts.waves_fonts import waves_font_origin
from ..utils.image import (
    add_footer,
    get_attribute_effect_sync,
    get_footer,
    get_square_avatar_sync,
    get_square_weapon_sync,
    get_weapon_type_sync,
)
from ..utils.resource.download_file import get_phantom_img

WIDTH = 1080
MARGIN = 40
GAP = 16
CONTENT_WIDTH = WIDTH - MARGIN * 2
TEXT = (235, 239, 241)
MUTED = (149, 164, 175)
TEAL = (119, 218, 199)
GOLD = (233, 203, 142)
PANEL = (24, 34, 45, 245)
BORDER = (56, 73, 85)
ATTR_COLORS = {
    "冷凝": (119, 189, 229),
    "热熔": (237, 134, 118),
    "导电": (193, 152, 234),
    "气动": (112, 211, 177),
    "衍射": (236, 213, 143),
    "湮灭": (204, 137, 185),
}


@lru_cache(maxsize=24)
def _font(size: int) -> ImageFont.FreeTypeFont:
    return waves_font_origin(size)


def _wrap_pixels(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """按实际字体宽度换行，不截断说明或长指令。"""
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        line = ""
        for char in paragraph:
            if line and font.getlength(line + char) > width:
                lines.append(line)
                line = ""
            line += char
        lines.append(line)
    return lines


def _compact(text: str) -> str:
    for old in ("附近队伍中所有角色", "队伍中所有角色", "队伍中的角色", "队伍中的所有共鸣者"):
        text = text.replace(old, "全队")
    return text.replace("下一位登场的共鸣者", "下一位").replace("下一位登场角色", "下一位").replace("，", ",")


def _rich_text(draw: ImageDraw.ImageDraw, position: tuple[int, int], text: str, size: int = 23) -> None:
    x, y = position
    for part in re.split(r"(\d+(?:\.\d+)?%|\d+层)", text):
        draw.text((x, y), part, font=_font(size), fill=GOLD if re.fullmatch(r"\d+(?:\.\d+)?%|\d+层", part) else TEXT)
        x += _font(size).getlength(part)


def _icon(image: Image.Image, asset: Image.Image, box: tuple[int, int, int, int]) -> None:
    x, y, w, h = box
    ImageDraw.Draw(image).rounded_rectangle((x, y, x + w, y + h), radius=min(14, w // 5), fill=(34, 47, 60), outline=BORDER)
    icon = ImageOps.contain(asset.convert("RGBA"), (w - 4, h - 4), Image.Resampling.LANCZOS)
    image.alpha_composite(icon, (x + (w - icon.width) // 2, y + (h - icon.height) // 2))


@lru_cache(maxsize=1)
def _echo_ids() -> dict[str, str]:
    return {data.get("name", "").removeprefix("共鸣回响·"): resource_id for resource_id, data in echo_id_data.items()}


async def _load_echo_icons(names: list[str]) -> dict[str, Image.Image]:
    icons = {}
    for name in dict.fromkeys(names):
        echo_id = _echo_ids().get(name)
        if echo_id:
            icons[name] = await get_phantom_img(int(echo_id), "")
    return icons


def _equipment_image(kind: str, name: str, weapon_id: int | None = None, echo_icons: dict | None = None) -> Image.Image:
    if kind == KIND_SONATA:
        return get_attribute_effect_sync(name)
    if kind == KIND_WEAPON:
        return get_square_weapon_sync(weapon_id or get_weapon_id(name) or "")
    return (echo_icons or {}).get(name) or get_attribute_effect_sync("")


def _panel(title: str, rows: list[dict], width: int = CONTENT_WIDTH, caption: str = "", accent: tuple = TEAL) -> Image.Image:
    label_width = 152
    value_x = 196
    value_width = width - value_x - 24
    layouts = []
    for row in rows:
        labels = _wrap_pixels(row.get("label", ""), _font(18), label_width)
        values = _wrap_pixels(_compact(row["value"]), _font(23), value_width)
        hints = _wrap_pixels(row.get("hint", ""), _font(18), value_width) if row.get("hint") else []
        height = max(len(labels) * 25, len(values) * 31 + len(hints) * 25) + 24
        layouts.append((row, labels, values, hints, height))
    top = 82 if caption else 60
    image = Image.new("RGBA", (width, top + sum(item[-1] for item in layouts) + 14))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, image.height - 1), radius=20, fill=PANEL, outline=BORDER)
    draw.rounded_rectangle((22, 23, 26, 43), radius=2, fill=accent)
    draw.text((38, 18), title, font=_font(26), fill=TEXT)
    if caption:
        draw.text((24, 53), caption, font=_font(18), fill=MUTED)
    y = top
    for index, (row, labels, values, hints, height) in enumerate(layouts):
        if index:
            draw.line((24, y - 9, width - 24, y - 9), fill=BORDER)
        for line_index, line in enumerate(labels):
            draw.text((24, y + line_index * 25), line, font=_font(18), fill=accent)
        for line_index, line in enumerate(values):
            _rich_text(draw, (value_x, y + line_index * 31), line)
        for line_index, line in enumerate(hints):
            draw.text((value_x, y + len(values) * 31 + line_index * 25), line, font=_font(18), fill=MUTED)
        y += height
    return image


class _Canvas:
    """先测量卡片，再按真实内容高度组合；不预留空白表格。"""

    def __init__(self, title: str, subtitle: str, role_id: int | None = None, attribute: str = "", weapon_type: str = ""):
        self.title = title
        self.subtitle = subtitle
        self.role_id = role_id
        self.attribute = attribute
        self.weapon_type = weapon_type
        self.blocks: list[Image.Image] = []
        self.texts: list[str] = [title, subtitle]

    def add(self, block: Image.Image, texts: list[str] | None = None) -> None:
        self.blocks.append(block)
        self.texts.extend(texts or [])

    def card(self, title: str, rows: list[dict], caption: str = "", accent: tuple = TEAL) -> None:
        if not rows:
            return
        self.add(
            _panel(title, rows, caption=caption, accent=accent),
            [title, caption] + [str(value) for row in rows for value in row.values()],
        )

    def _header_layout(self) -> tuple[int, list[str], list[str], int]:
        x = MARGIN + (100 if self.role_id is not None else 0)
        width = WIDTH - MARGIN - x - (156 if self.attribute or self.weapon_type else 0)
        size = 42
        while size > 24 and _font(size).getlength(self.title) > width:
            size -= 1
        titles = _wrap_pixels(self.title, _font(size), width)
        subtitles = _wrap_pixels(self.subtitle, _font(19), width)
        height = max(156, 51 + len(titles) * (size + 9) + len(subtitles) * 27 + 22)
        return size, titles, subtitles, height

    def height(self) -> int:
        return self._header_layout()[-1] + sum(block.height + GAP for block in self.blocks) + get_footer().height + 40

    def render(self) -> Image.Image:
        image = Image.new("RGBA", (WIDTH, self.height()), (15, 23, 32))
        draw = ImageDraw.Draw(image)
        # 装饰仅限页头，不让背景干扰长文本阅读。
        draw.polygon(((WIDTH - 340, 0), (WIDTH, 0), (WIDTH, 154), (WIDTH - 450, 154)), fill=(23, 41, 47))
        draw.text((MARGIN, 22), "WUTHERING WAVES  /  TEAMMATES", font=_font(15), fill=TEAL)
        x = MARGIN
        if self.role_id is not None:
            _icon(image, get_square_avatar_sync(self.role_id), (MARGIN, 54, 78, 78))
            x += 100
        size, titles, subtitles, header_height = self._header_layout()
        for index, line in enumerate(titles):
            draw.text((x, 51 + index * (size + 9)), line, font=_font(size), fill=TEXT)
        subtitle_y = 51 + len(titles) * (size + 9) + 3
        for index, line in enumerate(subtitles):
            draw.text((x, subtitle_y + index * 27), line, font=_font(19), fill=MUTED)
        if self.attribute:
            draw.text(
                (WIDTH - MARGIN, 62), self.attribute, font=_font(23), fill=ATTR_COLORS.get(self.attribute, TEAL), anchor="ra"
            )
        if self.weapon_type:
            draw.text((WIDTH - MARGIN, 97), self.weapon_type, font=_font(19), fill=MUTED, anchor="ra")
            _icon(image, get_weapon_type_sync(self.weapon_type), (WIDTH - MARGIN - 130, 93, 30, 30))
        y = header_height
        for block in self.blocks:
            image.alpha_composite(block, (MARGIN, y))
            y += block.height + GAP
        image = add_footer(image)
        return image


def _effect_rows(config: dict) -> tuple[list[dict], list[dict], dict[str, list[dict]]]:
    core, chains = [], []
    equipment: dict[str, list[dict]] = {KIND_SONATA: [], KIND_ECHO: [], KIND_WEAPON: []}
    weapon_names = [name for _, name in weapon_options()]
    for category in config.get("categories", []):
        for effect in category.get("effects", []):
            title = effect["title"]
            source = effect.get("source", category["key"])
            if source == "character" and any(title.startswith(name + "-") for name in weapon_names):
                source = KIND_WEAPON
            label = title.removeprefix(config["name"] + "-").removeprefix("固有技能-")
            if label == "延奏技能":
                label = "延奏"
            chain = effect.get("min_chain", 0)
            if chain:
                label = f"{chain}链 · {label}"
            chain_values = effect.get("chains", [])
            chain_hint = ""
            if chain_values and max(chain_values) < 6:
                chain_hint = f"仅{chain_values[0]}链" if len(chain_values) == 1 else f"{min(chain_values)}–{max(chain_values)}链"
            hint = " · ".join(
                dict.fromkeys(filter(None, [chain_hint, effect.get("state_hint", ""), effect.get("condition", "")]))
            )
            row = {"label": label, "value": effect["msg"], "hint": hint}
            if source in equipment:
                equipment[source].append(row)
            else:
                (chains if chain else core).append(row)
    # 延奏首先显示：这是换队友最直接的增益。
    core.sort(key=lambda row: 0 if row["label"] == "延奏" else 1)
    return core, chains, equipment


def _equipment_card(config: dict, effects: dict[str, list[dict]]) -> Image.Image | None:
    equip = config.get("equip", {})
    tiles = []
    selected = [
        (kind, label)
        for kind, label in ((KIND_SONATA, "合鸣"), (KIND_ECHO, "声骸"), (KIND_WEAPON, "专武 · 精1"))
        if equip.get(kind, {}).get("default")
    ]
    if not selected:
        return None
    tile_width = (CONTENT_WIDTH - 48 - GAP * (len(selected) - 1)) // len(selected)
    for kind, label in selected:
        data = equip[kind]
        name = data["default"]
        name_lines = _wrap_pixels(name, _font(22), tile_width - 92)
        rows = effects[kind]
        lines: list[tuple[str, bool]] = []
        for row in rows:
            lines.extend((line, False) for line in _wrap_pixels(_compact(row["value"]), _font(18), tile_width - 20))
            if row["hint"]:
                lines.extend((line, True) for line in _wrap_pixels(row["hint"], _font(16), tile_width - 20))
        tile_height = max(106, 90 + max(0, len(name_lines) - 1) * 28) + len(lines) * 25 + 18
        tile = Image.new("RGBA", (tile_width, tile_height))
        draw = ImageDraw.Draw(tile)
        draw.rounded_rectangle((0, 0, tile_width - 1, tile_height - 1), radius=14, fill=(31, 44, 56), outline=BORDER)
        _icon(tile, _equipment_image(kind, name, data.get("id"), config.get("echo_icons")), (12, 17, 62, 62))
        draw.text((88, 14), label, font=_font(16), fill=TEAL)
        for index, line in enumerate(name_lines):
            draw.text((88, 39 + index * 28), line, font=_font(22), fill=TEXT)
        y = max(106, 90 + max(0, len(name_lines) - 1) * 28)
        for line, hint in lines:
            draw.text((12, y), line, font=_font(16 if hint else 18), fill=MUTED if hint else GOLD)
            y += 25
        tiles.append(tile)
    if not tiles:
        return None
    image = Image.new("RGBA", (CONTENT_WIDTH, max(tile.height for tile in tiles) + 72))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=20, fill=PANEL, outline=BORDER)
    draw.text((24, 17), "默认装备", font=_font(26), fill=TEXT)
    for index, tile in enumerate(tiles):
        image.alpha_composite(tile, (24 + index * (tile_width + GAP), 56))
    return image


def build_teammate_canvas(config: dict, short_name: str = "") -> _Canvas:
    name = config["name"]
    canvas = _Canvas(
        f"{name} · 队友配置",
        "核心增益 / 默认装备 / 指令参数",
        config["role_id"],
        config.get("attribute", ""),
        config.get("weapon_type", ""),
    )
    core, chains, equipment = _effect_rows(config)
    canvas.card("核心增益", core, "0链可用 · 灰字为生效条件，金色为关键数值")
    canvas.card("共鸣链变化", chains, "达到对应链数生效 · 同名效果的不同数值分别列出", accent=GOLD)
    equip = _equipment_card(config, equipment)
    if equip is not None:
        canvas.add(
            equip,
            [
                data.get("default", "")
                for key, data in config.get("equip", {}).items()
                if key in (KIND_SONATA, KIND_ECHO, KIND_WEAPON)
            ]
            + [row["value"] for rows in equipment.values() for row in rows],
        )
    cases = config.get("equip", {}).get("cases", [])
    canvas.card("条件装备", [{"label": row["when"], "value": row["equip"]} for row in cases])
    states = []
    for spec in config.get("states", []):
        key = spec["key"]
        choices = spec.get("choices")
        if spec.get("type") == "bool":
            options = "开 / 关"
            default = "开" if spec.get("default") else "关"
        else:
            options = " / ".join(map(str, choices)) if choices else spec.get("hint", "整数")
            default = str(spec.get("default", ""))
        states.append({"label": key, "value": f"{options}    默认：{default}", "hint": spec.get("desc", "")})
    canvas.card("可调状态", states, "写在队友名后：[参数=值]；不写即使用默认值")
    commands = example_commands(config["role_id"], short_name=short_name)[:2]
    hints = [
        "角色61 = 6链·精1；装备替换：合鸣/声骸/武器=名称",
        "分项：延奏/合鸣/声骸/武器=开或关；角色增益=关关闭全部",
    ]
    canvas.card(
        "指令与开关",
        [
            {"label": "基础" if index == 0 else "调参示例", "value": command, "hint": hints[index]}
            for index, command in enumerate(commands)
        ],
        "全部可选装备：ww队友配置装备",
    )
    return canvas


def _overview_card(row: dict, width: int) -> Image.Image:
    image = Image.new("RGBA", (width, 114))
    draw = ImageDraw.Draw(image)
    color = ATTR_COLORS.get(row.get("attribute", ""), TEAL)
    draw.rounded_rectangle((0, 0, width - 1, image.height - 1), radius=16, fill=PANEL, outline=BORDER)
    draw.rounded_rectangle((0, 16, 3, 52), radius=1, fill=color)
    _icon(image, get_square_avatar_sync(row["role_id"]), (12, 13, 48, 48))
    name_size = 22
    while name_size > 16 and _font(name_size).getlength(row["name"]) > width - 82:
        name_size -= 1
    draw.text((72, 10), row["name"], font=_font(name_size), fill=TEXT)
    draw.text((72, 41), row.get("attribute", ""), font=_font(17), fill=color)
    weapon_type = row.get("weapon_type", "")
    _icon(image, get_weapon_type_sync(weapon_type), (128, 39, 24, 24))
    draw.text((158, 41), weapon_type, font=_font(17), fill=MUTED)
    sources = row.get("sources", [])
    if not sources:
        sources = [
            label
            for key, label in (("has_character_buff", "角色"), ("has_outro", "延奏"), ("has_weapon_buff", "专武"))
            if row.get(key)
        ]
        if row.get("equip", {}).get("sonata") or row.get("equip", {}).get("echo"):
            sources.append("装备")
    draw.text((14, 69), " · ".join(sources), font=_font(16), fill=TEAL)
    defaults = row.get("state_defaults", {})
    states = " / ".join(
        f"{key}={'开' if value is True else '关' if value is False else value}" for key, value in defaults.items()
    ) or " / ".join(row.get("states", []))
    state_lines = _wrap_pixels(states, _font(16), width - 28)
    # 状态只展示入口名，完整参数在单角色详情里，不挤占总览。
    if len(state_lines) > 1:
        states = " / ".join(row.get("states", []))
        state_lines = _wrap_pixels(states, _font(16), width - 28)
    draw.text((14, 90), state_lines[0] if state_lines else "", font=_font(16), fill=MUTED)
    return image


def build_overview_canvas() -> _Canvas:
    rows = teammate_overview()
    canvas = _Canvas("队友配置", f"{len(rows)} 位可选队友 · 按星级 → 属性 → 武器类型排序")
    card_width = (CONTENT_WIDTH - GAP * 2) // 3
    for star in sorted({min(row["star_level"] or 4, 5) for row in rows}, reverse=True):
        group = [row for row in rows if min(row["star_level"] or 4, 5) == star]
        title = Image.new("RGBA", (CONTENT_WIDTH, 38))
        draw = ImageDraw.Draw(title)
        draw.text((0, 1), f"{star}星角色", font=_font(25), fill=GOLD if star == 5 else TEAL)
        draw.text((CONTENT_WIDTH, 7), f"{len(group)} 位", font=_font(18), fill=MUTED, anchor="ra")
        canvas.add(title)
        for offset in range(0, len(group), 3):
            block = Image.new("RGBA", (CONTENT_WIDTH, 114))
            for index, row in enumerate(group[offset : offset + 3]):
                block.alpha_composite(_overview_card(row, card_width), (index * (card_width + GAP), 0))
            canvas.add(block, [str(row) for row in group[offset : offset + 3]])
    canvas.card(
        "使用方法",
        [
            {"label": "查看角色", "value": "ww队友配置心", "hint": "角色详情只展示该角色相关的增益和参数"},
            {
                "label": "指定队友",
                "value": "今汐伤害 换队友 心61 守岸人01",
                "hint": "最多两位队友；角色61 = 6链·专武精1，不写默认0链精1",
            },
            {
                "label": "换装备",
                "value": "ww队友配置装备",
                "hint": "集中查看可替换的合鸣、声骸和武器，不在每张角色详情里重复铺开",
            },
        ],
    )
    return canvas


def build_equipment_canvas(echo_icons: dict | None = None) -> _Canvas:
    canvas = _Canvas("队友装备目录", "可替换装备集中查看 · 只列已实现队友增益的装备")
    for kind, title in ((KIND_SONATA, "合鸣套装"), (KIND_ECHO, "首位声骸"), (KIND_WEAPON, "队友武器")):
        names = preset_names(kind) if kind != KIND_WEAPON else [name for _, name in weapon_options()]
        tile_width = (CONTENT_WIDTH - GAP * 2) // 3
        cards = []
        for name in names:
            card = Image.new("RGBA", (tile_width, 82))
            draw = ImageDraw.Draw(card)
            draw.rounded_rectangle((0, 0, card.width - 1, card.height - 1), radius=14, fill=PANEL, outline=BORDER)
            _icon(card, _equipment_image(kind, name, echo_icons=echo_icons), (12, 13, 54, 54))
            for index, line in enumerate(_wrap_pixels(name, _font(20), tile_width - 88)):
                draw.text((78, 18 + index * 26), line, font=_font(20), fill=TEXT)
            cards.append(card)
        heading = Image.new("RGBA", (CONTENT_WIDTH, 38))
        ImageDraw.Draw(heading).text((0, 1), f"{title}  ·  {len(names)}", font=_font(25), fill=TEAL)
        canvas.add(heading)
        for offset in range(0, len(cards), 3):
            block = Image.new("RGBA", (CONTENT_WIDTH, 82))
            for index, card in enumerate(cards[offset : offset + 3]):
                block.alpha_composite(card, (index * (tile_width + GAP), 0))
            canvas.add(block, names[offset : offset + 3])
    canvas.card(
        "替换写法",
        [
            {
                "label": "示例",
                "value": "今汐伤害 换队友 守岸人01[声骸=鸣钟之龟]",
                "hint": "合鸣/声骸/武器=关 可关闭对应来源；替换只影响本次计算",
            }
        ],
    )
    return canvas


def config_as_text(config: dict) -> str:
    core, chains, equipment = _effect_rows(config)
    lines = [f"{config['name']} · 队友配置"]
    for title, rows in (("核心增益", core), ("共鸣链变化", chains)):
        if rows:
            lines.append(f"\n{title}")
            lines.extend(f"{row['label']}：{row['value']}" + (f"（{row['hint']}）" if row["hint"] else "") for row in rows)
    for kind, label in ((KIND_SONATA, "合鸣"), (KIND_ECHO, "声骸"), (KIND_WEAPON, "武器")):
        name = config.get("equip", {}).get(kind, {}).get("default")
        if name:
            lines.append(f"{label}：{name}")
            lines.extend(row["value"] + (f"（{row['hint']}）" if row["hint"] else "") for row in equipment[kind])
    for spec in config.get("states", []):
        lines.append(f"{spec['key']}：默认{spec.get('default')}；{spec.get('desc', '')}")
    lines.extend(example_commands(config["role_id"])[:2])
    lines.append("全部可选装备：ww队友配置装备")
    return "\n".join(lines)


async def draw_teammate_config_img(role_id: int, short_name: str = "") -> Image.Image | str:
    try:
        config = detect_teammate(role_id)
    except TeamConfigError as exc:
        return str(exc)
    echo = config.get("equip", {}).get(KIND_ECHO, {}).get("default")
    config["echo_icons"] = await _load_echo_icons([echo] if echo else [])
    return build_teammate_canvas(config, short_name=short_name).render()


async def draw_teammate_overview_img() -> Image.Image:
    return build_overview_canvas().render()


async def draw_teammate_equipment_img() -> Image.Image:
    return build_equipment_canvas(await _load_echo_icons(preset_names(KIND_ECHO))).render()
