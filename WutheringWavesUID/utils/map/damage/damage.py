from ...api.model import RoleDetailData, WeaponData
from ...damage.abstract import WavesEchoRegister, WavesWeaponRegister
from ...damage.damage import DamageAttribute


def weapon_damage(
    attr: DamageAttribute,
    weapon_data: WeaponData,
    damage_func: list[str] | str,
    isGroup: bool,
):
    isGroup = isGroup or attr.group_mode
    # 武器谐振
    weapon_clz = WavesWeaponRegister.find_class(weapon_data.weapon.weaponId)
    if weapon_clz:
        w = weapon_clz(
            weapon_data.weapon.weaponId,
            weapon_data.level,
            weapon_data.breach,
            weapon_data.resonLevel,
        )
        w.do_action(damage_func, attr, isGroup)


def echo_damage(attr: DamageAttribute, isGroup: bool):
    isGroup = isGroup or attr.group_mode
    # 声骸计算
    echo_clz = WavesEchoRegister.find_class(attr.echo_id)
    if echo_clz:
        e = echo_clz()
        e.do_echo(attr, isGroup)


def phase_damage(
    attr: DamageAttribute,
    role: RoleDetailData,
    damage_func: list[str],
    isGroup: bool = False,
    isHealing: bool = False,
):
    from ...damage.register_sonata import get_sonata

    isGroup = isGroup or attr.group_mode
    for ph_detail in attr.ph_detail or ():
        sonata = get_sonata(ph_detail.ph_name, ph_detail.ph_num)
        if sonata:
            sonata.do_phase(attr, role, damage_func, isGroup, isHealing)
