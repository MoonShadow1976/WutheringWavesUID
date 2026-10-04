from ...utils.damage.abstract import CharAbstract, WavesCharRegister
from .damage import DamageAttribute, check_char_id
from .utils import (
    CHAR_ATTR_CELESTIAL,
    CHAR_ATTR_FREEZING,
    CHAR_ATTR_MOLTEN,
    CHAR_ATTR_SIERRA,
    CHAR_ATTR_SINKING,
    CHAR_ATTR_VOID,
    attack_damage,
    hit_damage,
    liberation_damage,
    phantom_damage,
    skill_damage,
    temp_atk,
    temp_def,
)


class Char_1102(CharAbstract):
    id = 1102
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "散华"
    starLevel = 4

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_template == temp_atk:
            if chain >= 6:
                title = "散华-六链"
                msg = "队伍中的角色攻击提升20%"
                attr.add_atk_percent(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attack_damage == attr.char_damage:
            title = "散华-延奏技能"
            msg = "下一位登场角色普攻伤害加深38%"
            attr.add_dmg_deepen(0.38, title, msg)


class Char_1103(CharAbstract):
    id = 1103
    name = "白芷"
    starLevel = 4

    teammate_states = {
        "天籁": {"type": "bool", "default": True, "desc": "主C拾取天籁，攻击加成15%，持续20秒"},
        "天籁拾取": {"type": "bool", "default": True, "desc": "队伍至少一人拾取天籁，六链冷凝加成生效"},
        "延奏治疗": {"type": "bool", "default": True, "desc": "下一位受到延奏治疗后的6秒窗口"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        # 固有技能按已解锁，默认主C拾取天籁且增益窗口有效。
        if states.get("天籁", True) and attr.char_template == temp_atk:
            attr.add_atk_percent(0.15, "白芷-天籁", "拾取天籁,攻击提升15%,20秒")
        if chain >= 6 and attr.char_attr == CHAR_ATTR_FREEZING:
            if states.get("天籁", True) or states.get("天籁拾取", True):
                attr.add_dmg_bonus(0.12, "白芷-六链", "队伍拾取天籁,冷凝加成12%,20秒")

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if (states or {}).get("延奏治疗", True):
            attr.add_dmg_deepen(0.15, "白芷-延奏技能", "下一位受到治疗,全伤加深15%,6秒")


class Char_1104(CharAbstract):
    id = 1104
    name = "凌阳"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 默认凌阳已施放延奏，队伍增益仍在30秒窗口内。
        if chain >= 4 and attr.char_attr == CHAR_ATTR_FREEZING:
            attr.add_dmg_bonus(0.2, "凌阳-四链", "延奏后冷凝加成20%,30秒")


class Char_1105(CharAbstract):
    id = 1105
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "折枝"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_template == temp_atk:
            if chain >= 4:
                title = f"{self.name}-四链"
                msg = "折枝施放共鸣解放虚实境趣时，队伍中角色攻击提升20%"
                attr.add_atk_percent(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_attr == CHAR_ATTR_FREEZING:
            title = f"{self.name}-延奏技能"
            msg = "下一位登场角色冷凝伤害加深20%"
            attr.add_dmg_bonus(0.2, title, msg)

        if skill_damage == attr.char_damage:
            title = f"{self.name}-延奏技能"
            msg = "下一位登场角色共鸣技能伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)


class Char_1106(CharAbstract):
    id = 1106
    name = "釉瑚"
    starLevel = 4

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.sync_strike:
            attr.add_dmg_deepen(1.0, "釉瑚-延奏技能", "下一位协同攻击加深100%,28秒")


class Char_1107(CharAbstract):
    id = 1107
    name = "珂莱塔"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_damage == skill_damage:
            attr.add_dmg_bonus(0.25, "珂莱塔-四链", "重击后技能加成25%,30秒")


class Char_1108(CharAbstract):
    id = 1108
    name = "绯雪"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4:
            attr.add_dmg_bonus(0.2, "绯雪-四链", "常世技能或霜罚后伤害提升20%,30秒")

    # 延奏 对拥有【霜渐效应】的敌人造成的冷凝伤害加深20%
    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_attr == CHAR_ATTR_FREEZING and attr.env_glacio_chafe:
            title = f"{self.name}-延奏技能"
            msg = "对有霜渐效应的敌人造成的冷凝伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)


class Char_1109(CharAbstract):
    id = 1109
    teammate_equip = {
        "sonata": "雪落无声之愿",
        "echo": "迷胧幻蛾",
        "weapon": {"id": 21050086},
        # 主C打声骸技能伤害时改带这套（原本写死在 _do_buff 的声骸模态分支里）
        "cases": [
            {"damage": phantom_damage, "sonata": "轻云出月", "echo": "无常凶鹭"},
        ],
    }
    name = "洛瑟菈"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.env_glacio_chafe and attr.char_attr == CHAR_ATTR_FREEZING and attr.char_damage != phantom_damage:
            attr.add_enemy_resistance(-0.08, "洛瑟菈-慢镜头", "霜渐模态追光后冷凝减抗8%,30秒")

        if attr.env_glacio_chafe:
            if attr.env_glacio_chafe_deepen:
                if chain >= 2:
                    title = f"{self.name}-二链-霜渐模态"
                    msg = "目标受到【霜渐效应】的伤害加深80%"
                    attr.add_dmg_deepen(0.8, title, msg)

        if phantom_damage == attr.char_damage:
            title = "固有技能-声骸模态"
            msg = "队伍中的角色声骸技能伤害加成提升25%"
            attr.add_dmg_bonus(0.25, title, msg)

            if chain >= 2:
                title = f"{self.name}-二链-声骸模态"
                msg = "队伍中角色的声骸技能伤害加成提升40%"
                attr.add_dmg_bonus(0.4, title, msg)

            title = "共鸣回路-变焦"
            msg = "4层变焦使角色声骸技能伤害的暴击伤害提升40%"
            attr.add_crit_dmg(0.4, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.env_glacio_chafe and attr.env_glacio_chafe_deepen:
            title = f"{self.name}-延奏技能"
            msg = "目标受到【霜渐效应】的伤害加深60%"
            attr.add_dmg_deepen(0.6, title, msg)

        if phantom_damage == attr.char_damage:
            title = f"{self.name}-延奏技能"
            msg = "下一位登场角色声骸技能伤害加深50%"
            attr.add_dmg_deepen(0.5, title, msg)


class Char_1110(CharAbstract):
    id = 1110
    teammate_equip = {
        "sonata": "羽落空尘之歌",
        "weapon": {"id": 21050096},
    }
    name = "穗穗"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 共鸣解放 消耗目标【虚湮效应】层数后，使自身造成的湮灭伤害无视目标6%防御，且无视目标12%湮灭抗性，持续30秒，该效果无法叠加。
        if attr.role is not None and attr.role.role.roleId == 1610:  # 先指定 sp秧秧
            title = "穗穗-共鸣解放-康衢之谣"
            msg = "消耗目标【虚湮效应】层数后，湮灭伤害无视目标6%防御"
            attr.add_defense_ignore(0.06, title, msg)
            msg = "消耗目标【虚湮效应】层数后，无视目标12%湮灭抗性"
            attr.add_enemy_resistance(-0.12, title, msg)

        if chain >= 2 and attr.is_env_abnormal():
            title = "穗穗-二链"
            msg = "山河水境内触发效果的角色暴击伤害提升50%"
            attr.add_crit_dmg(0.5, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "穗穗-延奏技能"
        msg = "队伍中的角色全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)

        title = "穗穗-延奏-400芳菲信"
        msg = "共鸣效率超200%每1%时提升0.2%伤害,上限12%"
        attr.add_dmg_bonus(0.12, title, msg)

        if attr.char_template == temp_atk:
            # 角色消耗目标【异常效应】或【电磁爆发】层数时
            # 1链后 角色为目标附加【异常效应】或造成异常效应伤害后，也可以触发
            title = "穗穗-延奏-600芳菲信"
            msg = "共鸣效率超200%每0.12%时提升0.1%攻击,上限50%"
            attr.add_atk_percent(0.5, title, msg)


class Char_1202(CharAbstract):
    id = 1202
    name = "炽霞"
    starLevel = 4

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 6 and attr.char_damage == attack_damage:
            attr.add_dmg_bonus(0.25, "炽霞-六链", "轰轰后普攻加成25%,15秒")


class Char_1203(CharAbstract):
    id = 1203
    name = "安可"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_attr == CHAR_ATTR_MOLTEN:
            attr.add_dmg_bonus(0.2, "安可-四链", "黑咩重击后热熔加成20%,30秒")


class Char_1204(CharAbstract):
    id = 1204
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
        "weapon": {"id": 21030015},
    }
    name = "莫特斐"
    starLevel = 4

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_template == temp_atk:
            if chain >= 6:
                title = "莫特斐-六链"
                msg = "施放共鸣解放暴烈终曲时，队伍中的角色攻击提升20%"
                attr.add_atk_percent(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if hit_damage == attr.char_damage:
            title = "莫特斐-延奏技能"
            msg = "下一位登场角色重击伤害加深38%"
            attr.add_dmg_deepen(0.38, title, msg)


class Char_1205(CharAbstract):
    id = 1205
    name = "长离"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_template == temp_atk:
            if chain >= 4:
                title = "长离-四链"
                msg = "施放变奏技能后，队伍中的角色攻击提升20%"
                attr.add_atk_percent(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_attr == CHAR_ATTR_MOLTEN:
            title = "长离-延奏技能"
            msg = "下一位登场角色热熔伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)

        if liberation_damage == attr.char_damage:
            title = "长离-延奏技能"
            msg = "下一位登场角色共鸣解放伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)


class Char_1206(CharAbstract):
    id = 1206
    name = "布兰特"
    starLevel = 5

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 下一位登场角色热熔伤害加深20%，共鸣技能伤害加深25%
        if attr.char_attr == CHAR_ATTR_MOLTEN:
            title = "布兰特-延奏技能"
            msg = "下一位登场角色热熔伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)

        if skill_damage == attr.char_damage:
            title = "布兰特-延奏技能"
            msg = "下一位登场角色共鸣解放伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)


class Char_1207(CharAbstract):
    id = 1207
    teammate_equip = {
        "sonata": "奔狼燎原之焰",
        "weapon": {"id": 21010036},
    }
    name = "露帕"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        def get_molten_num(
            attr: DamageAttribute,
        ):
            """
            获取热熔人数，队伍人数
            """
            fix_num = 1
            for char_id in attr.teammate_char_ids:
                if int(char_id) // 100 == 12:
                    fix_num += 1
            return fix_num, len(attr.teammate_char_ids) + 1

        molten_num, team_num = get_molten_num(attr)

        """获得buff"""
        # 奔狼燎原之焰 走目录，见上面的 teammate_equip

        if chain >= 2:
            title = "露帕-二链"
            msg = "施放共鸣解放时，队伍中的角色热熔伤害提升(20+20)%"
            attr.add_dmg_bonus(0.4, title, msg)

        if chain >= 3:
            title = "露帕-荣光效果-三链"
            msg = "角色攻击时无视15%热熔抗性"
            attr.add_enemy_resistance(-0.15, title, msg)
        else:
            # 共鸣解放·荣光
            # 施放共鸣解放荣光欢酣于火时，额外获得荣光效果，35秒内：
            # 队伍中的角色攻击时无视3%热熔抗性，并且队伍中每有一名除露帕外的热熔属性角色，无视热熔抗性效果增加3%，上限为9%，当队伍中的热熔属性角色达到3名时，无视热熔抗性的效果额外增加6%。
            title = "露帕-荣光效果"
            msg = f"角色攻击时无视3*{molten_num}%热熔抗性"
            attr.add_enemy_resistance(-0.03 * molten_num, title, msg)

            if molten_num >= 3:
                msg = "角色攻击时无视6%热熔抗性"
                attr.add_enemy_resistance(-0.06, title, msg)

        title = "露帕-追猎-共鸣解放"
        if molten_num >= 3 or chain >= 3:
            msg = "热熔提升(10+10)%"
            attr.add_dmg_bonus(0.2, title, msg)
        else:
            msg = "热熔提升10%"
            attr.add_dmg_bonus(0.1, title, msg)

        msg = f"攻击力提升(6*{team_num})%"
        attr.add_atk_percent(0.06 * team_num, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_attr == CHAR_ATTR_MOLTEN:
            title = "露帕-延奏技能"
            msg = "下一位登场角色热熔伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)

        if attack_damage == attr.char_damage:
            title = "露帕-延奏技能"
            msg = "下一位登场角色普攻伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)


class Char_1208(CharAbstract):
    id = 1208
    name = "嘉贝莉娜"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4:
            attr.add_dmg_bonus(0.2, "嘉贝莉娜-四链", "队伍施放声骸,全属性加成20%,20秒")


class Char_1209(CharAbstract):
    id = 1209
    teammate_equip = {
        "sonata": "星构寻辉之环",
        "weapon": {"id": 21010066},
    }
    name = "莫宁"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 谐振场
        title = "莫宁-谐振场"
        msg = "谐振场生效范围内偏谐值累积效率提升50%"
        attr.add_off_tune_buildup_rate(0.5, title, msg)

        if attr.char_template == temp_def:
            # 强谐振场
            title = "莫宁-强谐振场"
            msg = "强谐振场生效范围内附近队伍中所有角色防御提升20%"
            attr.add_def_percent(0.2, title, msg)

        # 干涉标记
        if attr.env_tune_rupture or attr.env_tune_strain or chain >= 1:
            title = "莫宁-干涉标记"
            tip = "若目标处于【震谐/集谐干涉】状态，对其" if chain < 1 else "队伍中角色"
            msg = f"{tip}造成的伤害提升40%"
            attr.add_dmg_bonus(0.4, title, msg)

        if chain >= 2:
            title = "莫宁-二链"
            msg = "角色对拥有干涉标记的目标造成的暴击伤害提升32%"
            attr.add_crit_dmg(0.32, title, msg)

            title = "莫宁-二链"
            msg = "谐振场还会使偏谐值累积效率额外提升20%"
            attr.add_off_tune_buildup_rate(0.2, title, msg)

        title = "莫宁-解耦"
        msg = "莫宁于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "莫宁-延奏技能"
        msg = "队伍中的角色全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)


class Char_1210(CharAbstract):
    id = 1210
    name = "爱弥斯"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4:
            title = "爱弥斯-四链"
            msg = "队伍中的角色全属性伤害加成提升20%"
            attr.add_dmg_bonus(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "爱弥斯-延奏技能"
        # ·处于共鸣模态·震谐时，队伍中除爱弥斯以外的角色全伤害加深10%，持续20秒。角色附加【震谐·偏移】时，该角色的该全伤害加深效果提升至20%
        # ·处于共鸣模态·聚爆时，队伍中除爱弥斯以外的角色全伤害加深10%，持续20秒。角色附加【聚爆效应】时，该角色的该全伤害加深效果提升至20%
        if attr.env_tune_rupture or attr.env_fusion_burst:
            msg = "角色附加聚爆效应或震谐·偏移时,全伤害加深效果提升至20%"
            attr.add_dmg_deepen(0.2, title, msg)
        else:
            msg = "队伍中除爱弥斯以外的角色全伤害加深10%"
            attr.add_dmg_deepen(0.1, title, msg)


class Char_1211(CharAbstract):
    id = 1211
    teammate_equip = {
        "sonata": "逆光跃彩之约",
        "echo": "海维夏",
        "weapon": {"id": 21050076},
        # 聚爆模态时改带这套（原本写死在 _do_buff 的聚爆分支里）
        "cases": [
            {"env": "env_fusion_burst", "sonata": "斑驳粉饰之沫", "echo": "达妮娅"},
        ],
    }
    name = "达妮娅"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.env_tune_strain:
            title = "达妮娅-固有技能·蚀刻繁彩"
            msg = "共鸣模态·集谐:谐度破坏增幅提升10点"
            attr.add_tune_break_boost(10, title, msg)

            dmg = min(40, (attr.off_tune_buildup_rate - 1) * 100 // 10 * 8)
            msg = f"共鸣模态·集谐:偏累超100%每10%谐破提升8点,上限40点,当前{dmg:,.0f}点"
            attr.add_tune_break_boost(dmg, title, msg)

            title = "达妮娅-计时的溃灭"
            msg = "达妮娅于编队中时，目标集谐·干涉层数上限增加1层"
            attr.add_tune_strain_stack(1, title, msg)

            if chain >= 2 and attr.env_tune_strain:
                title = "达妮娅-二链"
                msg = "施加【震谐·偏移】后，该角色谐度破坏增幅提升20点"
                attr.add_tune_break_boost(20, title, msg)

        if attr.env_fusion_burst:
            title = "达妮娅-固有技能·蚀刻繁彩"
            msg = "共鸣模态·聚爆:热熔伤害加成提升30%"
            attr.add_dmg_bonus(0.3, title, msg)

            if chain >= 2 and attr.env_fusion_burst:
                title = "达妮娅-二链"
                msg = "施加【聚爆效应】后，该角色热熔伤害加成提升50%"
                attr.add_dmg_bonus(0.5, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.env_tune_strain:
            title = "达妮娅-延奏技能"
            dmg = 0.15
            if attr.env_tune_strain:
                dmg = 0.4
            msg = f"下一个登场的角色全伤害加深{dmg * 100:.0f}%"
            attr.add_dmg_deepen(dmg, title, msg)

        if attr.env_fusion_burst:
            if attr.env_fusion_burst_deepen:
                title = "达妮娅-延奏技能"
                msg = "队伍中登场角色周围目标受到聚爆效应伤害加深60%"
                attr.add_dmg_deepen(0.6, title, msg)


class Char_1212(CharAbstract):
    id = 1212
    name = "景燃"
    starLevel = 5

    teammate_states = {
        "获盾": {"type": "bool", "default": True, "desc": "队伍有人获得护盾，四链30秒窗口有效，不视为主C获盾"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and (states or {}).get("获盾", True):
            # 队伍有人获盾不等于主C获盾，不设置trigger_shield。
            attr.add_dmg_bonus(0.2, "景燃-四链", "队伍获盾,全属性加成20%,30秒")


class Char_1301(CharAbstract):
    id = 1301
    name = "卡卡罗"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 默认已延奏，保留其持续30秒的全队共鸣链增益。
        if chain >= 4 and attr.char_attr == CHAR_ATTR_VOID:
            attr.add_dmg_bonus(0.2, "卡卡罗-四链", "延奏后导电加成20%,30秒")


class Char_1302(CharAbstract):
    id = 1302
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "吟霖"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_template == temp_atk:
            if chain >= 4:
                title = "吟霖-四链"
                msg = "共鸣回路审判之雷命中时，队伍中的角色攻击提升20%"
                attr.add_atk_percent(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 下一位登场角色导电伤害加深20%，共鸣解放伤害加深25%
        if attr.char_attr == CHAR_ATTR_VOID:
            title = "吟霖-延奏技能"
            msg = "下一位登场角色导电伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)

        if liberation_damage == attr.char_damage:
            title = "吟霖-延奏技能"
            msg = "下一位登场角色共鸣解放伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)


class Char_1303(CharAbstract):
    id = 1303
    name = "渊武"
    starLevel = 4

    teammate_states = {
        "雷楔": {"type": "bool", "default": True, "desc": "主C处于雷之楔范围内，六链防御提升32%"},
        "护盾": {"type": "bool", "default": True, "desc": "解放后10秒内，主C获得四链护盾"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        if chain >= 4 and states.get("护盾", True):
            attr.set_trigger_shield()
            attr.add_effect("渊武-四链", "解放后主C获盾,持续10秒")
        if chain >= 6 and states.get("雷楔", True) and attr.char_template == temp_def:
            attr.add_def_percent(0.32, "渊武-六链", "雷楔范围内防御提升32%,3秒")


class Char_1304(CharAbstract):
    id = 1304
    name = "今汐"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        attr.set_env_unison()
        attr.add_effect(f"{self.name}-常态", "共鸣技能惊龙破空后，今汐可获得同奏")

        if chain >= 4:
            attr.add_dmg_bonus(0.2, "今汐-四链", "解放或惊龙后全属性加成20%,20秒")


class Char_1305(CharAbstract):
    id = 1305
    name = "相里要"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_damage == liberation_damage:
            attr.add_dmg_bonus(0.25, "相里要-四链", "思维矩阵后解放加成25%,30秒")


class Char_1306(CharAbstract):
    id = 1306
    name = "奥古斯塔"
    starLevel = 5

    teammate_states = {
        "界域护盾": {"type": "bool", "default": True, "desc": "王之界域内主C施放变奏，获得护盾"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if (states or {}).get("界域护盾", True):
            attr.set_trigger_shield()
            attr.add_effect("奥古斯塔-王之界域", "假设界域内主C变奏获盾")
        if chain >= 4 and attr.char_template == temp_atk:
            attr.add_atk_percent(0.2, "奥古斯塔-四链", "变奏后队伍攻击提升20%,30秒")

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        attr.add_dmg_deepen(0.15, "奥古斯塔-延奏技能", "下一位全伤害加深15%,14秒")


class Char_1307(CharAbstract):
    id = 1307
    teammate_equip = {
        "sonata": "隐世回光",
        "echo": "无归的谬误",
    }
    name = "卜灵"
    starLevel = 4

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if skill_damage == attr.char_damage:
            if len(attr.teammate_char_ids) == 1:
                # 【雷法·两仪交泰】状态持续期间，使队伍中登场的角色共鸣技能伤害加成提升10%
                title = "卜灵-雷法·两仪交泰"
                msg = "队伍中登场的角色共鸣技能伤害加成提升10%"
                attr.add_dmg_bonus(0.1, title, msg)
            elif len(attr.teammate_char_ids) >= 2 and chain < 6:
                # 【雷法·三才合一】状态持续期间，使队伍中登场的角色共鸣技能伤害加成提升25%
                title = "卜灵-雷法·三才合一"
                msg = "队伍中登场的角色共鸣技能伤害加成提升25%"
                attr.add_dmg_bonus(0.25, title, msg)
            elif len(attr.teammate_char_ids) >= 2 and chain >= 6:
                # 【雷法·三才合一】状态持续期间，队伍中登场的角色获得的共鸣技能伤害加成效果提升至50%
                title = "卜灵-六链-雷法·三才合一"
                msg = "队伍中登场的角色共鸣技能伤害加成提升50%"
                attr.add_dmg_bonus(0.5, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 附近队伍中所有角色全伤害加深15%
        title = "卜灵-延奏技能"
        msg = "附近队伍中所有角色全伤害加深15%"
        attr.add_dmg_deepen(0.15, title, msg)


class Char_1308(CharAbstract):
    id = 1308
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
        "weapon": {"id": 21030066},
    }
    name = "丽贝卡"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 2:
            title = f"{self.name}-二链"
            msg = "队伍中的角色全属性伤害加成提升20%"
            attr.add_dmg_bonus(0.2, title, msg)

        if attr.env_hack:
            title = f"{self.name}-固有技能"
            msg = "附加【骇破·偏移】时，谐度破坏增幅提升30点"
            attr.add_tune_break_boost(30, title, msg)
            if chain >= 2:
                attr.add_dmg_deepen(0.15, "丽贝卡-二链", "附加骇破偏移,全伤加深15%,30秒")

        if attr.char_template == temp_atk:
            title = f"{self.name}-固有技能"
            msg = "施放共鸣解放后附近队伍中角色攻击提升20%"
            attr.add_atk_percent(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = f"{self.name}-延奏技能"
        msg = "下一位登场角色全伤害加深15%"
        attr.add_dmg_deepen(0.15, title, msg)
        if hit_damage == attr.char_damage:
            # 持有浪客羁绊的角色每0.2秒会获得1层超限，造成重击伤害加深0.5%（若是露西持有浪客羁绊，则直接获得满层），上限为35%
            dmg = 0.35 if check_char_id(attr, [1511]) else 0.2
            msg = f"持有浪客羁绊的角色重击伤害加深{dmg * 100:,.0f}%"
            attr.add_dmg_deepen(dmg, title, msg)


class Char_1310(CharAbstract):
    id = 1310
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "漂泊者·导电"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "雷主-固有技能-解明"
        msg = "共鸣技能超负荷对目标造成伤害后附加电磁效应"
        attr.set_env_electro_flare()
        attr.add_effect(title, msg)

        if attr.char_template == temp_atk:
            title = "雷主-共鸣回路-超负荷"
            msg = "短按施放超负荷，队伍中的角色获得10%攻击加成"
            attr.add_atk_percent(0.1, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "雷主-延奏技能"
        msg = "持有电髓的角色附加异常效应时，全伤害加深25%"
        attr.add_dmg_deepen(0.25, title, msg)


class Char_1309(Char_1310):
    id = 1309


class Char_1311(CharAbstract):
    id = 1311
    teammate_equip = {
        "sonata": "衔梦照世之心",
        "echo": "天演溯心",
    }
    name = "心"
    starLevel = 5
    teammate_states = {
        "模态": {
            "type": "enum",
            "choices": ["同奏", "电磁"],
            "default": "同奏",
            "desc": "共鸣模态：同奏给全队最终伤害与全属性加成，电磁给导电加深",
        },
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        mode = states.get("模态", "同奏")

        # 共鸣回路-响应同奏:队伍中的角色获得同奏增益
        # 基础1层+固有技能-信步拾清欢(四破)1层+六链1层,每层最终伤害提升3%,持续30秒
        if mode != "电磁":
            attr.set_env_unison()
            attr.add_effect(f"{self.name}-同奏模态", "施放共鸣解放·转相时，心获得同奏")

            attr.add_unison_stack(1, f"{self.name}-响应同奏", "获得1层同奏增益")

            # 固有 队伍中的角色【同奏增益】效果的层数上限增加1层，队伍中的角色响应同奏时，队伍中的角色获得1层【同奏增益】
            attr.unison_stack_max += 1
            attr.add_effect(f"{self.name}-固有技能", "同奏增益效果的层数上限增加1层")
            attr.add_unison_stack(1, f"{self.name}-固有技能", "响应同奏时，队伍中的角色获得1层同奏增益")

            if chain >= 6:
                title = f"{self.name}-六链"
                msg = "同奏增益效果的层数上限增加1层"
                attr.unison_stack_max += 1
                attr.add_effect(title, msg)

                attr.add_unison_stack(1, title, "响应同奏时，队伍中的角色获得1层同奏增益")

        # 四链:队伍中所有角色全属性伤害加成提升20%,持续30秒
        if chain >= 4:
            title = f"{self.name}-四链"
            msg = "队伍中所有角色全属性伤害加成提升20%,持续30秒"
            attr.add_dmg_bonus(0.2, title, msg)

        # 固有技能-循流引兴替(电磁模态):同编队有漂泊者·导电时,心和漂泊者·导电导电伤害加成提升20%
        if mode == "电磁" and (check_char_id(attr, [1309, 1310]) or not {1309, 1310}.isdisjoint(attr.teammate_char_ids or ())):
            title = "固有技能-循流引兴替"
            msg = "与漂泊者·导电同队,导电伤害加成提升20%,持续30秒"
            attr.add_dmg_bonus(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        mode = states.get("模态", "同奏")

        # 延奏技能:同奏模态给持有【灯同辉】的角色全伤害加深20%;电磁模态给队伍中除心之外的角色导电伤害加深20%
        title = f"{self.name}-延奏技能"
        if mode == "电磁":
            if attr.char_attr == CHAR_ATTR_VOID:
                msg = "电磁模态:队伍中角色导电伤害加深20%,持续20秒"
                attr.add_dmg_deepen(0.2, title, msg)
        else:
            msg = "同奏模态:持有【灯同辉】的角色全伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)


class Char_1312(CharAbstract):
    id = 1312
    teammate_equip = {
        "sonata": "镜影流电之瞬",
        "echo": "绝息魄",
        "weapon": {"id": 21020107},
    }
    name = "锁暝"
    starLevel = 5
    teammate_states = {
        "协契": {
            "type": "bool",
            "default": True,
            "desc": "协契是否生效（延奏给下一位角色的导电与暴击伤害加成）",
        },
    }

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}

        attr.set_env_unison()
        attr.add_effect(f"{self.name}-常态", "施放共鸣解放时，锁暝获得同奏")
        attr.add_unison_stack(1, f"{self.name}-响应同奏", "获得1层同奏增益")
        from gsuid_core.logger import logger

        logger.success(f"获得同奏增益:{attr.env_unison}")
        # 延奏技能:下一位登场角色导电伤害加深20%;拥有同奏增益时共鸣技能伤害加深25%,持续8秒
        title = f"{self.name}-延奏技能"
        if attr.char_attr == CHAR_ATTR_VOID:
            msg = "下一位登场角色导电伤害加深20%,持续8秒"
            attr.add_dmg_deepen(0.2, title, msg)
        if skill_damage == attr.char_damage:
            msg = "拥有同奏增益时下一位角色共鸣技能伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)

        if states.get("协契", True) and attr.char_attr == CHAR_ATTR_VOID:
            # 固有技能-沉契凝锁(四破):协契期间延奏,下一位角色导电伤害加成提升30%,每层同奏增益额外20%,最多40%
            title = "固有技能-沉契凝锁"
            extra = min(0.2 * attr.unison_stack_max, 0.4)
            msg = f"协契延奏:下一位角色导电伤害加成提升30%,同奏增益额外{extra * 100:.0f}%"
            attr.add_dmg_bonus(0.3 + extra, title, msg)

        # 二链:延奏时下一位登场角色暴击伤害提升10%,每层同奏增益额外6%,最多24%,持续30秒
        if chain >= 2:
            title = f"{self.name}-二链"
            extra = min(0.06 * attr.unison_stack_max, 0.24)
            msg = f"延奏:下一位角色暴击伤害提升10%,同奏增益额外{extra * 100:.0f}%"
            attr.add_crit_dmg(0.1 + extra, title, msg)


class Char_1402(CharAbstract):
    id = 1402
    name = "秧秧"
    starLevel = 4

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 6 and attr.char_template == temp_atk:
            attr.add_atk_percent(0.2, "秧秧-六链", "施放释羽后攻击提升20%,20秒")


class Char_1403(CharAbstract):
    id = 1403
    name = "秋水"
    starLevel = 4

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_attr == CHAR_ATTR_SIERRA:
            attr.add_dmg_deepen(0.23, "秋水-延奏技能", "下一位气动伤害加深23%,14秒")


class Char_1404(CharAbstract):
    id = 1404
    name = "忌炎"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_damage == hit_damage:
            attr.add_dmg_bonus(0.25, "忌炎-四链", "解放后重击伤害加成25%,30秒")


class Char_1405(CharAbstract):
    id = 1405
    name = "鉴心"
    starLevel = 5

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_damage == liberation_damage:
            attr.add_dmg_deepen(0.38, "鉴心-延奏技能", "下一位共鸣解放伤害加深38%,14秒")


class Char_1406(CharAbstract):
    id = 1406
    teammate_equip = {
        "sonata": "流云逝尽之空",
        "weapon": {"id": 21020046},
    }
    name = "漂泊者·气动"
    starLevel = 5


class Char_1407(CharAbstract):
    id = 1407
    name = "夏空"
    starLevel = 5
    teammate_states = {
        "音律独奏": {"type": "bool", "default": True, "desc": "夏空或合奏音影进入音律独奏，24%气动加成不可叠加"},
        "解放": {"type": "bool", "default": True, "desc": "歌者的三重华彩期间，二链提供40%气动加成"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        if attr.char_attr == CHAR_ATTR_SIERRA:
            if states.get("音律独奏", True):
                attr.add_dmg_bonus(0.24, "夏空-音律独奏", "音律独奏气动加成24%,不可叠加")
            if chain >= 2 and states.get("解放", True):
                attr.add_dmg_bonus(0.4, "夏空-二链", "解放期间气动伤害加成40%")

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.env_aero_erosion_deepen:
            attr.add_dmg_deepen(1.0, "夏空-延奏技能", "仅风蚀效应伤害加深100%,30秒")


class Char_1408(Char_1406):
    id = 1408
    name = "漂泊者·气动"
    starLevel = 5


class Char_1409(CharAbstract):
    id = 1409
    name = "卡提希娅"
    starLevel = 5

    teammate_states = {
        "异常目标": {"type": "bool", "default": True, "desc": "目标持有异常效应，延奏气动加深生效"},
        "附加异常": {"type": "bool", "default": True, "desc": "队伍附加常规异常后20秒，四链全属性加成生效"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and (states or {}).get("附加异常", True):
            attr.add_dmg_bonus(0.2, "卡提希娅-四链", "附加异常后全属性加成20%,20秒")

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if (states or {}).get("异常目标", True) and attr.char_attr == CHAR_ATTR_SIERRA and not check_char_id(attr, [1409]):
            attr.add_dmg_deepen(0.175, "卡提希娅-延奏技能", "异常目标气动伤害加深17.5%,20秒")


class Char_1410(CharAbstract):
    id = 1410
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "尤诺"
    starLevel = 5
    teammate_states = {
        "祝福层数": {
            "type": "int",
            "min": 0,
            "max": 10,
            "default": 10,
            "desc": "苍白死光的祝颂层数，每层全伤害加深4%；叠满10层时二链额外+40%",
        },
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        # 苍白死光的祝颂：默认按满层10层计算
        stacks = int(states.get("祝福层数", 10))
        if stacks:
            title = "尤诺-苍白死光的祝颂"
            msg = f"满月领域中获得十次护盾后，角色全伤害加深4%*{stacks}"
            attr.add_dmg_deepen(0.04 * stacks, title, msg)

        if chain >= 2 and stacks >= 10:
            title = "尤诺-二链"
            msg = "苍白死光的祝颂叠加至10层时额外获得40%全伤害加深"
            attr.add_dmg_deepen(0.4, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if hit_damage == attr.char_damage:
            title = "尤诺-延奏技能"
            msg = "下一位登场角色重击伤害加深50%"
            attr.add_dmg_deepen(0.5, title, msg)


class Char_1411(CharAbstract):
    id = 1411
    teammate_equip = {
        "sonata": "息界同调之律",
        "weapon": {"id": 21020066},
    }
    name = "仇远"
    starLevel = 5
    teammate_states = {
        "暴击增益": {
            "type": "bool",
            "default": True,
            "desc": "仇远自身暴击是否达到65%，达到时给登场角色+30%暴击伤害",
        },
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        # 共鸣解放爆伤提升（需要仇远自身暴击至少65%）
        if states.get("暴击增益", True):
            title = "仇远-共鸣解放爆伤提升"
            msg = "仇远暴击至少65%时，登场角色提升30%暴击伤害"
            attr.add_crit_dmg(0.3, title, msg)

        if phantom_damage == attr.char_damage:
            # 息界同调之律 走目录，见上面的 teammate_equip

            # 竹照
            title = "仇远-竹照"
            msg = "附近队伍中登场角色声骸技能伤害加成提升30%"
            attr.add_dmg_bonus(0.3, title, msg)

            if chain >= 2:
                title = "仇远-二链"
                msg = "竹照额外效果：附近队伍中角色声骸技能伤害加深30%"
                attr.add_dmg_deepen(0.3, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if phantom_damage == attr.char_damage:
            title = "仇远-延奏技能"
            msg = "下一位登场角色声骸技能伤害加深50%"
            attr.add_dmg_deepen(0.5, title, msg)


class Char_1412(CharAbstract):
    id = 1412
    name = "西格莉卡"
    starLevel = 5
    teammate_states = {
        "祝福层数": {
            "type": "int",
            "min": 0,
            "max": 6,
            "default": 6,
            "desc": "语义的祝福层数，每层给队伍中登场角色3%气动/声骸技能伤害加成",
        },
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        # 每层语义的祝福使队伍中登场角色气动伤害加成提升3%，声骸技能伤害加成提升3%
        # 默认按满层6层计算
        stacks = int(states.get("祝福层数", 6))
        title = "西格莉卡-固有技能-语义共鸣"
        if stacks:
            value = 0.03 * stacks
            if attr.char_attr == CHAR_ATTR_SIERRA:
                msg = f"{stacks}层语义的祝福使队伍中登场角色气动伤害加成提升{value:.0%}"
                attr.add_dmg_bonus(value, title, msg)
            if attr.char_damage == phantom_damage:
                msg = f"{stacks}层语义的祝福使队伍中登场角色声骸技能伤害加成提升{value:.0%}"
                attr.add_dmg_bonus(value, title, msg)

        # 队伍中的角色施放声骸技能时，使队伍中的角色攻击提升20%，持续20秒
        if chain >= 4:
            title = "西格莉卡-四链"
            msg = "队伍中的角色释放声骸技能时,使队伍中的角色攻击提升20%"
            attr.add_atk_percent(0.2, title, msg)


class Char_1413(CharAbstract):
    id = 1413
    name = "清宵"
    starLevel = 5

    teammate_states = {
        "附加集谐": {"type": "bool", "default": True, "desc": "主C亲自附加集谐·偏移后的8秒窗口"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and (states or {}).get("附加集谐", True) and attr.char_template == temp_atk:
            attr.add_atk_percent(0.2, "清宵-四链", "本角色附加集谐后攻击提升20%,8秒")


class Char_1501(CharAbstract):
    id = 1501
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "漂泊者·衍射"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        """获得buff"""
        attr.set_env_spectro()
        title = "光主"
        msg = "触发光噪效应"
        attr.add_effect(title, msg)
        if chain >= 6 and attr.char_attr == CHAR_ATTR_CELESTIAL:
            title = "光主-六链"
            msg = "施放共鸣技能时，目标衍射伤害抗性降低10%"
            attr.add_enemy_resistance(-0.1, title, msg)


class Char_1502(Char_1501):
    id = 1502
    name = "漂泊者·衍射"
    starLevel = 5


class Char_1503(CharAbstract):
    id = 1503
    teammate_equip = {
        "sonata": "隐世回光",
        "echo": "鸣钟之龟",
    }
    name = "维里奈"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_template == temp_atk:
            title = "维里奈-固有技能-自然的献礼"
            msg = "队伍中的角色攻击提升20%"
            attr.add_atk_percent(0.2, title, msg)

        if chain >= 4 and attr.char_attr == CHAR_ATTR_CELESTIAL:
            title = "维里奈-四链"
            msg = "队伍中的角色衍射伤害加成提升15%"
            attr.add_dmg_bonus(0.15, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "维里奈-延奏技能"
        msg = "队伍中的角色全伤害加深15%"
        attr.add_dmg_deepen(0.15, title, msg)


class Char_1504(CharAbstract):
    id = 1504
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "灯灯"
    starLevel = 4

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_template == temp_atk:
            if chain >= 6:
                title = f"{self.name}-六链"
                msg = "施放共鸣解放时，队伍中的角色的攻击提升20%"
                attr.add_atk_percent(0.2, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if skill_damage == attr.char_damage:
            title = f"{self.name}-延奏技能"
            msg = "下一位登场角色共鸣技能伤害加深38%"
            attr.add_dmg_deepen(0.38, title, msg)


class Char_1505(CharAbstract):
    id = 1505
    teammate_equip = {
        "sonata": "隐世回光",
        "echo": "无归的谬误",
        "weapon": {"id": 21050036},
    }
    name = "守岸人"
    starLevel = 5
    teammate_states = {
        "领域": {
            "type": "bool",
            "default": True,
            "desc": "共鸣解放领域是否生效（暴击提升12.5% + 暴击伤害提升25%）",
        },
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        if attr.char_template == temp_atk:
            if chain >= 2:
                title = "守岸人-二链"
                msg = "队伍中的角色攻击提升40%"
                attr.add_atk_percent(0.4, title, msg)

        if states.get("领域", True):
            title = "守岸人-共鸣解放"
            msg = "暴击提升12.5%+暴击伤害提升25%"
            attr.add_crit_rate(0.125)
            attr.add_crit_dmg(0.25)
            attr.add_effect(title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "守岸人-延奏技能"
        msg = "队伍中的角色全伤害加深15%"
        attr.add_dmg_deepen(0.15, title, msg)


class Char_1506(CharAbstract):
    id = 1506
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
        "weapon": {"id": 21050046},
    }
    name = "菲比"
    starLevel = 5
    teammate_states = {
        "模式": {
            "type": "enum",
            "choices": ("告解", "赦罪"),
            "default": "告解",
            "desc": "告解：减少目标衍射抗性10%；赦罪：不减抗",
        },
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        if chain >= 4 and attr.char_attr == CHAR_ATTR_CELESTIAL:
            attr.add_enemy_resistance(-0.1, "菲比-四链", "普攻或闪避命中后衍射减抗10%,30秒")
        attr.set_env_spectro()
        title = "菲比"
        msg = "触发光噪效应"
        attr.add_effect(title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        # 默认告解模式：减少目标衍射抗性
        if states.get("模式", "告解") == "告解" and attr.char_attr == CHAR_ATTR_CELESTIAL:
            title = "菲比-延奏技能-告解"
            msg = "使一定范围内的目标衍射伤害抗性减少10%"
            attr.add_enemy_resistance(-0.1, title, msg)

        if states.get("模式", "告解") == "告解" and attr.env_spectro_deepen:
            title = f"{self.name}-延奏技能-告解"
            msg = "下一个变奏登场角色【光噪效应】伤害加深100%。"
            attr.add_dmg_deepen(1, title, msg)

            if chain >= 2:
                title = f"{self.name}-二链"
                msg = "告解状态下，默祷的【光噪效应】伤害加深效果额外提升120%。"
                attr.add_dmg_deepen(1.2, title, msg)


class Char_1507(CharAbstract):
    id = 1507
    name = "赞妮"
    starLevel = 5

    teammate_states = {
        "余烬目标": {"type": "bool", "default": False, "desc": "目标重新拥有烈阳余烬；延奏自身伤害会先清空余烬"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_template == temp_atk:
            attr.add_atk_percent(0.2, "赞妮-四链", "变奏后队伍攻击提升20%,30秒")

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if (states or {}).get("余烬目标", False) and attr.char_attr == CHAR_ATTR_CELESTIAL and not check_char_id(attr, [1507]):
            attr.add_dmg_deepen(0.2, "赞妮-延奏技能", "余烬目标衍射伤害加深20%,20秒")


class Char_1508(CharAbstract):
    id = 1508
    teammate_equip = {
        "weapon": {"id": 21010056},
    }
    name = "千咲"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        attr.set_env_havoc_bane()

        title = "千咲-共鸣回路-虚湮之线"
        msg = "对拥有虚无绞痕的目标造成伤害时，可无视其18%防御"
        attr.add_defense_ignore(0.18, title, msg)

        # 虚湮效应（6层）
        title = "虚湮效应"
        msg = "虚湮效应持续时，目标防御每层降低2%，目前降低6*2%"
        attr.add_defense_reduction(0.12, title, msg)

        # 二链效果
        if chain >= 2:
            title = "千咲-二链"
            msg = "队伍中的角色处于虚湮之线状态时，全属性伤害加成提升50%"
            attr.add_dmg_bonus(0.5, title, msg)

        # 六链效果：异常效应伤害加深
        if chain >= 6 and attr.is_env_abnormal_deepen():
            title = "千咲-六链"
            msg = "拥有虚无绞痕·终焉的目标受到异常效应伤害加深30%"
            attr.add_dmg_deepen(0.3, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 异常效应层数上限增加3层
        title = "千咲-延奏技能-解弦式第零定律"
        msg = "使目标层数上限增加3层"
        attr.add_effect(title, msg)
        # 注：这个记得单独写，是几层就是几层


class Char_1509(CharAbstract):
    id = 1509
    teammate_equip = {
        "sonata": "逆光跃彩之约",
        "echo": "海维夏",
        "weapon": {"id": 21030046},
    }
    name = "琳奈"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 附加集谐·偏移 - 光致变染
        title = "琳奈-共鸣模态"
        msg = "光致变染为目标附加【集谐·偏移】"
        attr.set_env_tune_strain()
        attr.add_effect(title, msg)

        title = "琳奈-共鸣回路-视觉冲击"
        msg = "消耗3点【本色】，使附近队伍中所有角色的谐度破坏增幅提升40点"
        attr.add_tune_break_boost(40, title, msg)

        title = "琳奈-共鸣解放"
        msg = "施放时使附近队伍中所有角色的伤害加成提升24%，持续30秒"
        attr.add_dmg_bonus(0.24, title, msg)

        title = "琳奈-光谱解析"
        msg = "琳奈于编队中时，目标集谐·干涉层数上限增加1层"
        attr.add_tune_strain_stack(1, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        title = "琳奈-延奏技能"
        msg = "下一个登场的角色全伤害加深15%，持续14秒"
        attr.add_dmg_deepen(0.15, title, msg)

        if chain >= 2:
            title = "琳奈-二链"
            msg = "延奏技能额外使下一个登场的角色全伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)

        if attr.char_damage == liberation_damage:
            title = "琳奈-延奏技能"
            msg = "下一个登场的角色共鸣解放伤害加深25%，持续14秒"
            attr.add_dmg_deepen(0.25, title, msg)


class Char_1510(CharAbstract):
    id = 1510
    name = "陆·赫斯"
    starLevel = 5

    teammate_states = {
        "谐度破坏": {"type": "bool", "default": True, "desc": "队伍造成谐度破坏伤害后的20秒窗口"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and (states or {}).get("谐度破坏", True):
            attr.add_dmg_bonus(0.2, "陆·赫斯-四链", "谐度破坏后伤害提升20%,20秒")


class Char_1511(CharAbstract):
    id = 1511
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
        "weapon": {"id": 21030015},
    }
    name = "露西"
    starLevel = 5
    teammate_targets = (1308, 1511)
    teammate_states = {
        "网络层数": {"type": "int", "min": 0, "max": 2, "default": 2, "desc": "网络后门仅露西/丽贝卡受益，每层10%，2层额外5%"},
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.env_hack:
            if chain >= 4:
                title = f"{self.name}-四链"
                msg = "附加【骇破·偏移】后角色全属性伤害加成提升20%"
                attr.add_dmg_bonus(0.2, title, msg)

        stacks = int((states or {}).get("网络层数", 2))
        if stacks and check_char_id(attr, self.teammate_targets):
            deepen = 0.1 * stacks + (0.05 if stacks >= 2 else 0)
            title = f"{self.name}-固有技能-网络后门"
            msg = f"仅露西/丽贝卡,网络{stacks}层全伤加深{deepen * 100:g}%"
            attr.add_dmg_deepen(deepen, title, msg)

        # 共鸣解放
        title = "欺骗程式·义体故障"
        msg = "使所有标记目标受到伤害提升5%,30秒"
        attr.add_dmg_bonus(0.05, title, msg)

        title = "欺骗程式·突破协议"
        msg = "使所有标记目标降低5%的防御"
        attr.add_defense_reduction(0.05, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attack_damage == attr.char_damage:
            title = f"{self.name}-延奏技能"
            msg = "下一名登场角色普攻伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)

        if attr.env_hack:
            title = f"{self.name}-延奏技能"
            msg = "附加【骇破·偏移】时，该角色全伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)


class Char_1601(CharAbstract):
    id = 1601
    name = "桃祈"
    starLevel = 4

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_damage == skill_damage:
            attr.add_dmg_deepen(0.38, "桃祈-延奏技能", "下一位共鸣技能伤害加深38%,14秒")


class Char_1602(CharAbstract):
    id = 1602
    teammate_equip = {
        "sonata": "幽夜隐匿之帷",
    }
    name = "丹瑾"
    starLevel = 4

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 6 and attr.char_template == temp_atk:
            attr.add_atk_percent(0.2, "丹瑾-六链", "施放缭乱后队伍攻击提升20%,20秒")

    # 下一位登场角色湮灭伤害加深23%，效果持续14秒，若切换至其他角色则该效果提前结束。

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if CHAR_ATTR_SINKING == attr.char_attr:
            title = "丹瑾-延奏技能"
            msg = "下一位登场角色湮灭伤害加深23%"
            attr.add_dmg_deepen(0.23, title, msg)


class Char_1603(CharAbstract):
    id = 1603
    name = "椿"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_damage == attack_damage:
            attr.add_dmg_bonus(0.25, "椿-四链", "变奏后普攻伤害加成25%,30秒")


class Char_1604(CharAbstract):
    id = 1604
    name = "漂泊者·湮灭"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_attr == CHAR_ATTR_SINKING:
            attr.add_enemy_resistance(-0.1, "漂泊者·湮灭-四链", "灭音或解放命中后湮灭减抗10%,20秒")


class Char_1605(Char_1604):
    id = 1605
    name = "漂泊者·湮灭"
    starLevel = 5


class Char_1606(CharAbstract):
    id = 1606
    teammate_equip = {
        "sonata": "轻云出月",
        "echo": "无常凶鹭",
    }
    name = "洛可可"
    starLevel = 5

    # 下一位登场角色湮灭伤害加深20%，普攻伤害加深25%，效果持续14秒，若切换至其他角色则该效果提前结束。
    teammate_states = {
        "固定攻击": {
            "type": "int",
            "min": 0,
            "max": 200,
            "default": 200,
            "desc": "共鸣解放提供的固定攻击力，上限200",
        },
    }

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        states = states or {}
        if attr.char_template == temp_atk:
            atk_flat = int(states.get("固定攻击", 200))
            if atk_flat:
                title = "洛可可-共鸣解放"
                msg = "施放共鸣解放最多提供200点攻击" if atk_flat == 200 else f"施放共鸣解放提供{atk_flat}点攻击"
                attr.add_atk_flat(atk_flat, title, msg)

        if CHAR_ATTR_SINKING == attr.char_attr:
            if chain >= 2:
                # 施放普攻幻想照进现实时，队伍中的角色湮灭伤害加成提升10%，可叠加3层
                title = "洛可可-二链"
                msg = "队伍中的角色湮灭伤害提升10%*4"
                attr.add_dmg_bonus(0.1 * 4, title, msg)

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attack_damage == attr.char_damage:
            title = "洛可可-延奏技能"
            msg = "下一位登场角色普攻伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)

        if CHAR_ATTR_SINKING == attr.char_attr:
            title = "洛可可-延奏技能"
            msg = "下一位登场角色湮灭伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)


class Char_1607(CharAbstract):
    id = 1607
    teammate_equip = {
        "sonata": "幽夜隐匿之帷",
    }
    name = "坎特蕾拉"
    starLevel = 5

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 下一位登场角色湮灭伤害加深20%，共鸣技能伤害加深25%
        if CHAR_ATTR_SINKING == attr.char_attr:
            title = "坎特蕾拉-延奏技能"
            msg = "下一位登场角色湮灭伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)

        if skill_damage == attr.char_damage:
            title = "坎特蕾拉-延奏技能"
            msg = "下一位登场角色共鸣技能伤害加深25%"
            attr.add_dmg_deepen(0.25, title, msg)


class Char_1608(CharAbstract):
    id = 1608
    name = "弗洛洛"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4:
            attr.add_dmg_bonus(0.2, "弗洛洛-四链", "施放声骸后全属性加成20%,30秒")

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if attr.char_attr == CHAR_ATTR_SINKING:
            attr.add_dmg_deepen(0.2, "弗洛洛-延奏技能", "下一位湮灭伤害加深20%,14秒")
        if attr.char_damage == hit_damage:
            attr.add_dmg_deepen(0.25, "弗洛洛-延奏技能", "下一位重击伤害加深25%,14秒")


class Char_1610(CharAbstract):
    id = 1610
    name = "秧秧·玄翎"
    starLevel = 5

    def _do_buff(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        if chain >= 4 and attr.char_template == temp_atk:
            attr.add_atk_percent(0.2, "秧秧·玄翎-四链", "变奏或指定技能后攻击提升20%,20秒")

    def _do_outro(
        self,
        attr: DamageAttribute,
        chain: int = 0,
        resonLevel: int = 1,
        isGroup: bool = True,
        states: dict | None = None,
    ):
        # 延奏 队伍中除秧秧·玄翎以外的角色，获得移宫换羽状态，持续20秒，移宫换羽持续期间为目标附加【虚湮效应】后，该角色湮灭伤害加深20%
        if CHAR_ATTR_SINKING == attr.char_attr and attr.env_havoc_bane:
            title = "秧秧·玄翎-延奏技能"
            msg = "为目标附加【虚湮效应】后，湮灭伤害加深20%"
            attr.add_dmg_deepen(0.2, title, msg)


def register_char():
    # 自动注册所有以 Char_ 开头的类
    for name, obj in globals().items():
        if name.startswith("Char_") and hasattr(obj, "id"):
            WavesCharRegister.register_class(obj.id, obj)
