import copy
from pathlib import Path

from gsuid_core.models import Event
from gsuid_core.utils.image.convert import convert_img
from PIL import Image, ImageDraw

from ..utils.api.model import (
    BatchRoleCostResponse,
    CultivateCost,
    OnlineRole,
    OnlineRoleList,
    OnlineWeapon,
    OnlineWeaponList,
    OwnedRoleList,
    RoleCostDetail,
    RoleCultivateStatusList,
    RoleDetailData,
)
from ..utils.ascension.char import get_char_model
from ..utils.ascension.material import get_material_model
from ..utils.ascension.weapon import get_weapon_model
from ..utils.char_info_utils import get_all_role_detail_info_list
from ..utils.database.models import WavesBind
from ..utils.error_reply import WAVES_CODE_098, WAVES_CODE_102, WAVES_CODE_103
from ..utils.fonts.waves_fonts import (
    waves_font_20,
    waves_font_32,
    waves_font_40,
)
from ..utils.hint import error_reply
from ..utils.image import (
    SPECIAL_GOLD,
    add_footer,
    get_square_avatar,
    get_square_weapon,
    get_waves_bg,
)
from ..utils.name_convert import (
    char_id_to_char_name,
    char_name_to_char_id,
    weapon_name_to_weapon_id,
)
from ..utils.refresh_char_detail import refresh_char
from ..utils.resource.constant import SPECIAL_CHAR
from ..utils.resource.download_file import get_material_img
from ..utils.waves_api import waves_api

skillBreakList = ["2-1", "2-2", "2-3", "2-4", "2-5", "3-1", "3-2", "3-3", "3-4", "3-5"]

template_role_develop = {
    "roleId": 0,
    "roleStartLevel": 1,
    "roleEndLevel": 90,
    "skillLevelUpList": [
        {"startLevel": 1, "endLevel": 10},
        {"startLevel": 1, "endLevel": 10},
        {"startLevel": 1, "endLevel": 10},
        {"startLevel": 1, "endLevel": 10},
        {"startLevel": 1, "endLevel": 10},
    ],
    "advanceSkillList": [
        "2-1",
        "2-2",
        "2-3",
        "2-4",
        "2-5",
        "3-1",
        "3-2",
        "3-3",
        "3-4",
        "3-5",
    ],
    "weaponStartLevel": 1,
    "weaponEndLevel": 90,
    "_category": "all",  # all self
    # "weaponId": 0,
}

TEXT_PATH = Path(__file__).parent / "texture2d"
material_star_1 = Image.open(TEXT_PATH / "material-star-1.png")
material_star_2 = Image.open(TEXT_PATH / "material-star-2.png")
material_star_3 = Image.open(TEXT_PATH / "material-star-3.png")
material_star_4 = Image.open(TEXT_PATH / "material-star-4.png")
material_star_5 = Image.open(TEXT_PATH / "material-star-5.png")
material_star_img_map = {
    1: material_star_1,
    2: material_star_2,
    3: material_star_3,
    4: material_star_4,
    5: material_star_5,
}

star_1 = Image.open(TEXT_PATH / "star-1.png")
star_2 = Image.open(TEXT_PATH / "star-2.png")
star_3 = Image.open(TEXT_PATH / "star-3.png")
star_4 = Image.open(TEXT_PATH / "star-4.png")
star_5 = Image.open(TEXT_PATH / "star-5.png")
star_img_map = {
    1: star_1,
    2: star_2,
    3: star_3,
    4: star_4,
    5: star_5,
}


skill_name_list = [
    "常态攻击",
    "共鸣技能",
    "共鸣回路",
    "共鸣解放",
    "变奏技能",
    "其他技能",
]

skill_index_kuro = {
    "常态攻击": 0,
    "共鸣技能": 1,
    "共鸣解放": 2,
    "变奏技能": 3,
    "共鸣回路": 4,
    "延奏技能": 5,
    "其他技能": 6,
}


async def calc_develop_cost(ev: Event, develop_list: list[str], is_flush=False):
    user_id = ev.user_id
    uid = await WavesBind.get_uid_by_game(user_id, ev.bot_id)
    if not uid:
        return error_reply(WAVES_CODE_103)
    if waves_api.is_net(uid):
        return error_reply(WAVES_CODE_098)

    token_result, token = await waves_api.get_ck_result(uid, user_id, ev.bot_id)
    if not token_result or not token:
        return error_reply(WAVES_CODE_102)

    alias_char_ids = []
    for develop in develop_list:
        char_id = char_name_to_char_id(develop)
        if char_id is None:
            continue
        alias_char_ids.append(char_id)

    if not alias_char_ids:
        return "未找到养成角色"

    if len(alias_char_ids) > 2:
        return "暂不支持查询两个以上角色养成"

    refresh_data = await waves_api.calculator_refresh_data(uid, token)
    if not refresh_data.success:
        return "养成刷新失败"

    # 获取所有角色
    online_list_role = await waves_api.get_online_list_role(token)
    if not online_list_role.success or isinstance(online_list_role.data, str):
        return online_list_role.throw_msg()
    online_list_role_model = OnlineRoleList.model_validate(online_list_role.data)
    online_role_map = {str(i.roleId): i for i in online_list_role_model}
    # 获取所有武器
    online_list_weapon = await waves_api.get_online_list_weapon(token)
    if not online_list_weapon.success or isinstance(online_list_weapon.data, str):
        return online_list_weapon.throw_msg()
    online_list_weapon_model = OnlineWeaponList.model_validate(online_list_weapon.data)
    online_weapon_map = {str(i.weaponId): i for i in online_list_weapon_model}
    # 获取拥有的角色
    owned_role = await waves_api.get_owned_role(uid, token)
    if not owned_role.success or isinstance(owned_role.data, str):
        return owned_role.throw_msg()
    owned_char_ids_model = OwnedRoleList.model_validate(owned_role.data)
    owned_char_ids = [str(i) for i in owned_char_ids_model]

    owneds = []
    not_owneds = []
    for char_id in alias_char_ids:
        if char_id not in online_role_map:
            continue
        if char_id in SPECIAL_CHAR:
            find_char_ids = SPECIAL_CHAR[char_id]
            for find_char_id in find_char_ids:
                if find_char_id in owned_char_ids:
                    char_id = find_char_id
                    break
        if char_id in owned_char_ids:
            owneds.append(char_id)
        else:
            not_owneds.append(char_id)

    develop_data_map = {}
    if owneds:
        develop_data = await waves_api.get_develop_role_cultivate_status(uid, token, owneds)
        if not develop_data.success:
            return develop_data.throw_msg()
        develop_data = RoleCultivateStatusList.model_validate(develop_data.data)
        develop_data_map = {i.roleId: i for i in develop_data}

    if is_flush:
        waves_datas = await refresh_char(ev, uid, user_id, ck=token)
        if isinstance(waves_datas, str):
            return waves_datas
    else:
        waves_datas = await get_all_role_detail_info_list(uid)
        if not waves_datas:
            return "未找到养成角色"

    content_list = []
    for no_owned_char_id in not_owneds:
        template_role = copy.deepcopy(template_role_develop)
        template_role["roleId"] = no_owned_char_id

        char_name = char_id_to_char_name(no_owned_char_id)
        if char_name:
            weapon_id = weapon_name_to_weapon_id(f"{char_name}专武")
            if weapon_id:
                template_role["weaponId"] = weapon_id

        content_list.append(template_role)

    for r in waves_datas:
        if isinstance(r, RoleDetailData):
            role_detail = r
        else:
            role_detail = RoleDetailData.model_validate(r)
        char_id = role_detail.role.roleId
        if char_id not in develop_data_map:
            continue
        develop_data = develop_data_map[char_id]
        template_role = copy.deepcopy(template_role_develop)
        template_role["roleId"] = char_id
        template_role["roleStartLevel"] = develop_data.roleLevel

        for skill in develop_data.skillLevelList:
            if skill.type == "其他技能" or skill.type == "延奏技能" or skill.type == "谐度破坏":
                continue

            skill_index = skill_index_kuro[skill.type]
            template_role["skillLevelUpList"][skill_index]["startLevel"] = skill.level

        template_role["weaponId"] = role_detail.weaponData.weapon.weaponId
        template_role["weaponStartLevel"] = role_detail.weaponData.level
        template_role["advanceSkillList"] = list(set(skillBreakList).difference(set(develop_data.skillBreakList)))
        content_list.append(template_role)

    if not content_list:
        return "未找到养成角色"

    develop_cost = await waves_api.get_batch_role_cost(uid, token, content_list)
    if not develop_cost.success:
        return develop_cost.throw_msg()
    content_map = {f"{i['roleId']}": i for i in content_list}

    batch_role_cost_res = BatchRoleCostResponse.model_validate(develop_cost.data)

    all_card = []
    # batch_preview: RoleCostDetail = batch_role_cost_res.preview
    for cost in batch_role_cost_res.costList:
        role_detail_card = await calc_role_need_card(cost, online_role_map, online_weapon_map, content_map)
        all_card.extend(role_detail_card)

    height_block = 40
    material_height = 0
    for img in all_card:
        material_height += img.size[1] + height_block

    height = material_height + 50
    card_img = get_waves_bg(1100, height, "bg8")

    temp_height = 0
    for img in all_card:
        card_img.alpha_composite(img, (20, temp_height))
        temp_height += img.size[1] + height_block
    card_img = add_footer(card_img)
    card_img = await convert_img(card_img)
    return card_img


async def mock_calc_develop_cost(develop_list: list[str]):
    alias_char_ids = []
    for name in develop_list:
        cid = char_name_to_char_id(name)
        if cid:
            alias_char_ids.append(cid)
    if not alias_char_ids:
        return "未找到养成角色"
    if len(alias_char_ids) > 2:
        return "暂不支持查询两个以上角色养成"

    # 构造养成数据
    content_role_map = {}
    content_weapon_map = {}
    content_map = {}
    cost_details = []
    for cid in alias_char_ids:
        role = get_char_model(cid)
        if not role:
            return "未找到养成角色"
        content_role_map[str(cid)] = OnlineRole(
            roleId=cid,
            roleName=role.name,
            roleIconUrl="",
            starLevel=role.starLevel,
            attributeId=role.attributeId,
            weaponTypeId=role.weaponTypeId,
            weaponTypeName="",
            acronym="",
            isPreview=False,
            isNew=False,
            priority=1,
        )

        weapon_name = f"{role.name}专武"
        weapon_id = weapon_name_to_weapon_id(weapon_name)
        weapon = get_weapon_model(weapon_id) if weapon_id else None
        if weapon and weapon_id:
            content_weapon_map[str(weapon_id)] = OnlineWeapon(
                weaponId=int(weapon_id),
                weaponName=weapon.name,
                weaponType=weapon.type,
                weaponStarLevel=weapon.starLevel,
                weaponIcon="",
                acronym="",
                isPreview=False,
                isNew=False,
                priority=1,
            )

        template = copy.deepcopy(template_role_develop)
        template["roleId"] = cid
        template["weaponId"] = weapon_id
        content_map[str(cid)] = template

        # 养成材料
        mock_all_costs: dict[str, CultivateCost] = {}
        mock_role_costs: dict[str, CultivateCost] = {}
        mock_skill_costs: dict[str, CultivateCost] = {}
        mock_weapon_costs: dict[str, CultivateCost] = {}

        # 角色养成材料
        for ascensions in role.ascensions.values():
            for m in ascensions:
                material = get_material_model(m.key)
                if material:
                    m_cost = CultivateCost(
                        id=str(m.key),
                        name=material.name,
                        iconUrl="",
                        num=int(m.value or 0),
                        type=material.type,
                        quality=material.rarity,
                        isPreview=False,
                    )
                    if str(m.key) in mock_role_costs:
                        mock_role_costs[str(m.key)].num += m_cost.num
                    else:
                        mock_role_costs[str(m.key)] = m_cost

        # 角色技能养成材料
        for skills in role.skillTree.values():
            for skill in skills.values():
                if not skill.consume:
                    continue
                for consume in skill.consume.values():
                    for m in consume:
                        material = get_material_model(m.key)
                        if material:
                            m_cost = CultivateCost(
                                id=str(m.key),
                                name=material.name,
                                iconUrl="",
                                num=int(m.value or 0),
                                type=material.type,
                                quality=material.rarity,
                                isPreview=False,
                            )
                            if str(m.key) in mock_skill_costs:
                                mock_skill_costs[str(m.key)].num += m_cost.num
                            else:
                                mock_skill_costs[str(m.key)] = m_cost

        # 武器养成材料
        if weapon:
            for ascensions in weapon.ascensions.values():
                for m in ascensions:
                    material = get_material_model(m.key)
                    if material:
                        m_cost = CultivateCost(
                            id=str(m.key),
                            name=material.name,
                            iconUrl="",
                            num=int(m.value or 0),
                            type=material.type,
                            quality=material.rarity,
                            isPreview=False,
                        )
                        if str(m.key) in mock_weapon_costs:
                            mock_weapon_costs[str(m.key)].num += m_cost.num
                        else:
                            mock_weapon_costs[str(m.key)] = m_cost

        # 合并到mock_all_costs
        for cost_dict in (mock_role_costs, mock_skill_costs, mock_weapon_costs):
            for mid, m in cost_dict.items():
                if mid in mock_all_costs:
                    mock_all_costs[mid].num += m.num
                else:
                    mock_all_costs[mid] = m.model_copy()

        cost_detail = RoleCostDetail(
            allCost=list(mock_all_costs.values()),
            missingCost=None,  # 不需要"仍需材料"
            synthetic=None,
            missingRoleCost=list(mock_role_costs.values()),
            missingSkillCost=list(mock_skill_costs.values()),
            missingWeaponCost=list(mock_weapon_costs.values()),
            roleId=cid,
            weaponId=content_map[str(cid)].get("weaponId"),
            strategyList=None,
            showStrategy=False,
        )
        cost_details.append(cost_detail)

    all_card = []
    for cost in cost_details:
        role_card = await calc_role_need_card(cost, content_role_map, content_weapon_map, content_map)
        all_card.extend(role_card)

    height_block = 40
    material_height = 0
    for img in all_card:
        material_height += img.size[1] + height_block
    height = material_height + 50
    card_img = get_waves_bg(1100, height, "bg8")
    temp_height = 0
    for img in all_card:
        card_img.alpha_composite(img, (20, temp_height))
        temp_height += img.size[1] + height_block
    card_img = add_footer(card_img)
    card_img = await convert_img(card_img)
    return card_img


async def draw_material_card(cultivate_cost_list: list[CultivateCost], title: str):
    line_item_num = 6
    material_header_height = 120
    material_header_block_height = 20
    material_item_width = 144
    material_item_height = 170
    material_item_block_height = 30

    allCostNum = len(cultivate_cost_list)
    allCost_height = (allCostNum + line_item_num - 1) // line_item_num
    temp_high = material_header_block_height
    material_header_img = Image.open(TEXT_PATH / "material-header.png")
    material_header_img_draw = ImageDraw.Draw(material_header_img)
    material_header_img_draw.text(
        (50, 40),
        title,
        fill=(255, 255, 255, 255),
        font=waves_font_32,
    )

    cultivate_cost_img = Image.new(
        "RGBA",
        (
            material_header_img.size[0],
            allCost_height * (material_item_height + material_item_block_height)
            + material_header_height
            + material_header_block_height * 2,
        ),
    )
    # 绘制阴影
    cultivate_cost_img_draw = ImageDraw.Draw(cultivate_cost_img)
    cultivate_cost_img_draw.rectangle(
        [20, 20, cultivate_cost_img.size[0], cultivate_cost_img.size[1]],
        fill=(255, 255, 255, int(0.8 * 255)),
    )
    cultivate_cost_img.alpha_composite(material_header_img, (20, temp_high))

    temp_high += material_header_block_height + material_header_height
    index = 0
    for cultivate_cost in cultivate_cost_list:
        temp_img = Image.new("RGBA", (material_item_width, material_item_height), (0, 0, 0, 255))

        material_star_img = copy.deepcopy(material_star_img_map[cultivate_cost.quality])
        material_item_img = await get_material_img(cultivate_cost.id)
        material_item_img = material_item_img.resize((material_item_width, material_item_width))

        temp_img_draw = ImageDraw.Draw(temp_img)
        temp_img_draw.text(
            (72, 155),
            f"{cultivate_cost.num}",
            fill=(255, 255, 255, 255),
            font=waves_font_20,
            anchor="mm",
        )

        temp_img.alpha_composite(material_item_img, (0, 0))
        temp_img.alpha_composite(material_star_img, (0, 0))

        cultivate_cost_img.alpha_composite(
            temp_img,
            (
                40 + index % 6 * (material_item_width + 18),
                index // 6 * (material_item_height + material_item_block_height) + temp_high,
            ),
        )
        index += 1

    return cultivate_cost_img


async def calc_role_need_card(
    role_cost_detail: RoleCostDetail,
    online_role_map: dict[str, OnlineRole],
    online_weapon_map: dict[str, OnlineWeapon],
    content_map: dict[str, dict],
):
    img_cards = []
    if not role_cost_detail.roleId:
        return img_cards

    if f"{role_cost_detail.roleId}" not in online_role_map or f"{role_cost_detail.roleId}" not in content_map:
        return img_cards

    online_role = online_role_map[f"{role_cost_detail.roleId}"]

    content = content_map[f"{role_cost_detail.roleId}"]
    top_bg_img = Image.open(TEXT_PATH / "top-bg.png")
    top_bg_img_draw = ImageDraw.Draw(top_bg_img)

    # 角色头像
    square_avatar = await get_square_avatar(role_cost_detail.roleId)
    square_avatar = square_avatar.resize((180, 180))
    star_img = copy.deepcopy(star_img_map[online_role.starLevel])
    top_bg_img.alpha_composite(square_avatar, (70, 40))
    top_bg_img.alpha_composite(star_img, (70, 40))
    top_bg_img_draw.text(
        (280, 100),
        online_role.roleName,
        fill="white",
        font=waves_font_40,
    )
    top_bg_img_draw.text(
        (280, 150),
        f"Lv.{content['roleStartLevel']} -> Lv.{content['roleEndLevel']}",
        fill=SPECIAL_GOLD,
        font=waves_font_32,
    )

    # 武器
    if content.get("weaponId", None) and role_cost_detail.weaponId:
        online_weapon = online_weapon_map[f"{role_cost_detail.weaponId}"]
        weapon_id = content["weaponId"]
        square_weapon = await get_square_weapon(weapon_id)
        square_weapon = square_weapon.resize((180, 180))
        star_img = copy.deepcopy(star_img_map[online_weapon.weaponStarLevel])
        top_bg_img.alpha_composite(square_weapon, (530, 40))
        top_bg_img.alpha_composite(star_img, (530, 40))
        top_bg_img_draw.text(
            (750, 100),
            online_weapon.weaponName,
            fill="white",
            font=waves_font_40,
        )
        top_bg_img_draw.text(
            (750, 150),
            f"Lv.{content['weaponStartLevel']} -> Lv.{content['weaponEndLevel']}",
            fill=SPECIAL_GOLD,
            font=waves_font_32,
        )

    skill_img = Image.new(
        "RGBA",
        (
            top_bg_img.size[0],
            400,
        ),
    )

    skill_img_draw = ImageDraw.Draw(skill_img)
    skill_img_draw.rectangle(
        [0, 0, skill_img.size[0], skill_img.size[1]],
        fill=(255, 255, 255, int(0.8 * 255)),
    )
    for i, skill_name in enumerate(skill_name_list):
        skill_img_draw.text(
            (80 + (i % 2) * 470, 50 + i // 2 * 120),
            skill_name,
            fill="black",
            font=waves_font_32,
        )
        if skill_name != "其他技能":
            skill_index = skill_index_kuro[skill_name]
            skill_level = content["skillLevelUpList"][skill_index]
            skill_img_draw.text(
                (80 + (i % 2) * 470, 100 + i // 2 * 120),
                f"Lv.{skill_level['startLevel']} -> Lv.{skill_level['endLevel']}",
                fill=SPECIAL_GOLD,
                font=waves_font_32,
            )
        else:
            skill_img_draw.text(
                (80 + (i % 2) * 470, 100 + i // 2 * 120),
                "全选",
                fill=SPECIAL_GOLD,
                font=waves_font_32,
            )

    temp_img = Image.new(
        "RGBA",
        (
            10 + top_bg_img.size[0],
            20 + top_bg_img.size[1] + skill_img.size[1],
        ),
    )
    temp_img.alpha_composite(top_bg_img, (10, 20))
    temp_img.alpha_composite(skill_img, (10, 20 + top_bg_img.size[1]))
    img_cards.append(temp_img)

    if role_cost_detail.allCost:
        all_cost_img = await draw_material_card(role_cost_detail.allCost, "所需材料总览")
        img_cards.append(all_cost_img)

    if role_cost_detail.missingCost:
        missing_cost_img = await draw_material_card(role_cost_detail.missingCost, "仍需材料总览")
        img_cards.append(missing_cost_img)

    if role_cost_detail.missingRoleCost:
        missing_role_cost_img = await draw_material_card(role_cost_detail.missingRoleCost, "角色升级")
        img_cards.append(missing_role_cost_img)

    if role_cost_detail.missingSkillCost:
        missing_skill_cost_img = await draw_material_card(role_cost_detail.missingSkillCost, "技能升级")
        img_cards.append(missing_skill_cost_img)

    if role_cost_detail.missingWeaponCost:
        missing_weapon_cost_img = await draw_material_card(role_cost_detail.missingWeaponCost, "武器升级")
        img_cards.append(missing_weapon_cost_img)

    return img_cards
