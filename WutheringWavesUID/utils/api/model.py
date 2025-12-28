from typing import Literal

from msgspec import UNSET, Struct, UnsetType, field
from pydantic import BaseModel, Field, RootModel, model_validator


class GeneralGeetestData(Struct):
    geetest_challenge: str
    geetest_seccode: str
    geetest_validate: str


class GeneralV1SendPhoneCodeRequest(Struct):
    phone: str
    type: int
    captcha: GeneralGeetestData | UnsetType = field(default=UNSET)


class EnergyData(BaseModel):
    """结晶波片"""

    name: str
    img: str
    refreshTimeStamp: int
    cur: int
    total: int


class LivenessData(BaseModel):
    """活跃度"""

    name: str
    img: str
    cur: int
    total: int


class BattlePassData(BaseModel):
    """电台"""

    name: str
    cur: int
    total: int


class DailyData(BaseModel):
    """每日数据"""

    gameId: int
    userId: int
    serverId: str
    roleId: str
    roleName: str
    signInTxt: str
    hasSignIn: bool
    energyData: EnergyData
    livenessData: LivenessData
    battlePassData: list[BattlePassData]


class Role(BaseModel):
    roleId: int
    level: int
    breach: int | None = None
    roleName: str
    roleIconUrl: str | None
    rolePicUrl: str | None
    starLevel: int
    attributeId: int
    attributeName: str | None
    weaponTypeId: int
    weaponTypeName: str | None
    acronym: str
    chainUnlockNum: int | None = None
    # mapRoleId: int | None


class RoleList(BaseModel):
    roleList: list[Role]
    showRoleIdList: list[int] | None = None
    showToGuest: bool


class Box(BaseModel):
    boxName: str
    num: int


class Box2(BaseModel):
    name: str
    num: int


class AccountBaseInfo(BaseModel):
    """账户基本信息"""

    name: str  # 名字
    id: int  # 特征码
    creatTime: int | None = None  # 创建时间 ms
    activeDays: int | None = None  # 活跃天数
    level: int | None = None  # 等级
    worldLevel: int | None = None  # 世界等级
    roleNum: int | None = None  # 角色数量
    bigCount: int | None = None  # 大型信标解锁数
    smallCount: int | None = None  # 小型信标解锁数
    achievementCount: int | None = None  # 成就数量
    achievementStar: int | None = None  # 成就星数
    boxList: list[Box | None] | None = None  # 宝箱
    treasureBoxList: list[Box2 | None] | None = None  # 宝箱
    tidalHeritagesList: list[Box2 | None] | None = None  # 潮汐之遗
    weeklyInstCount: int | None = None  # 周本次数
    weeklyInstCountLimit: int | None = None  # 周本限制次数
    storeEnergy: int | None = None  # 结晶单质数量
    storeEnergyLimit: int | None = None  # 结晶单质限制
    rougeScore: int | None = None  # 千道门扉的异想
    rougeScoreLimit: int | None = None  # 千道门扉的异想限制

    @property
    def is_full(self):
        """完整数据，没有隐藏库街区数据"""
        return isinstance(self.creatTime, int)


class Chain(BaseModel):
    name: str | None
    order: int
    description: str | None
    iconUrl: str | None
    unlocked: bool


class Weapon(BaseModel):
    weaponId: int
    weaponName: str
    weaponType: int
    weaponStarLevel: int
    weaponIcon: str | None
    weaponEffectName: str | None
    # effectDescription: Optional[str]


class WeaponData(BaseModel):
    weapon: Weapon
    level: int
    breach: int | None = None
    resonLevel: int | None


class PhantomProp(BaseModel):
    phantomPropId: int
    name: str
    phantomId: int
    quality: int
    cost: int
    iconUrl: str
    skillDescription: str | None


class FetterDetail(BaseModel):
    groupId: int
    name: str
    iconUrl: str | None
    num: int
    firstDescription: str | None
    secondDescription: str | None


class Props(BaseModel):
    attributeName: str
    iconUrl: str | None = None
    attributeValue: str


class EquipPhantom(BaseModel):
    phantomProp: PhantomProp
    cost: int
    quality: int
    level: int
    fetterDetail: FetterDetail
    mainProps: list[Props] | None = None
    subProps: list[Props] | None = None

    def get_props(self):
        props = []
        if self.mainProps:
            props.extend(self.mainProps)
        if self.subProps:
            props.extend(self.subProps)

        return props


class EquipPhantomData(BaseModel):
    cost: int
    equipPhantomList: list[EquipPhantom | None] | None | list[None] = None


class Skill(BaseModel):
    id: int
    type: str
    name: str
    description: str
    iconUrl: str


class SkillData(BaseModel):
    skill: Skill
    level: int


class RoleDetailData(BaseModel):
    role: Role
    level: int
    chainList: list[Chain]
    weaponData: WeaponData
    phantomData: EquipPhantomData | None = None
    skillList: list[SkillData]

    def get_chain_num(self):
        """获取命座数量"""
        num = 0
        for index, chain in enumerate(self.chainList):
            if chain.unlocked:
                num += 1
        return num

    def get_chain_name(self):
        n = self.get_chain_num()
        return f"{['零', '一', '二', '三', '四', '五', '六'][n]}链"

    def get_skill_level(
        self,
        skill_type: Literal["常态攻击", "共鸣技能", "共鸣解放", "变奏技能", "共鸣回路"],
    ):
        skill_level = 1
        _skill = next((skill for skill in self.skillList if skill.skill.type == skill_type), None)
        if _skill:
            skill_level = _skill.level - 1
        return skill_level

    def get_skill_list(self):
        sort = ["常态攻击", "共鸣技能", "共鸣回路", "共鸣解放", "变奏技能", "延奏技能", "谐度破坏"]
        return sorted(self.skillList, key=lambda x: sort.index(x.skill.type))


class CalabashData(BaseModel):
    """数据坞"""

    level: int | None  # 数据坞等级
    baseCatch: str | None  # 基础吸收概率
    strengthenCatch: str | None  # 强化吸收概率
    catchQuality: int | None  # 最高可吸收品质
    cost: int | None  # cost上限
    maxCount: int | None  # 声骸收集进度-max
    unlockCount: int | None  # 声骸收集进度-curr
    isUnlock: bool  # 解锁


class KuroRoleInfo(BaseModel):
    """库洛角色信息"""

    id: int
    userId: int
    gameId: int
    serverId: str
    serverName: str
    roleId: str
    roleName: str
    gameHeadUrl: str
    roleNum: int
    achievementCount: int


class KuroWavesUserInfo(BaseModel):
    """库洛用户信息"""

    id: int
    userId: int
    gameId: int
    serverId: str
    roleId: str
    roleName: str


class GachaLog(BaseModel):
    """抽卡记录"""

    cardPoolType: str
    resourceId: int
    qualityLevel: int
    resourceType: str
    name: str
    count: int
    time: str

    def __hash__(self):
        return hash((self.resourceId, self.time))


# 定义角色模型
class AbyssRole(BaseModel):
    roleId: int
    iconUrl: str | None = None


# 定义楼层模型
class AbyssFloor(BaseModel):
    floor: int
    picUrl: str
    star: int
    roleList: list[AbyssRole] | None = None


# 定义区域模型
class AbyssArea(BaseModel):
    areaId: int
    areaName: str
    star: int
    maxStar: int
    floorList: list[AbyssFloor] | None = None


# 定义难度模型
class AbyssDifficulty(BaseModel):
    difficulty: int
    difficultyName: str
    towerAreaList: list[AbyssArea]


# 定义顶层模型
class AbyssChallenge(BaseModel):
    isUnlock: bool
    seasonEndTime: int | None
    difficultyList: list[AbyssDifficulty] | None


class ChallengeRole(BaseModel):
    roleName: str
    roleHeadIcon: str
    roleLevel: int


class Challenge(BaseModel):
    challengeId: int
    bossHeadIcon: str
    bossIconUrl: str
    bossLevel: int
    bossName: str
    passTime: int
    difficulty: int
    roles: list[ChallengeRole] | None = None


class ChallengeArea(BaseModel):
    challengeInfo: dict[str, list[Challenge]]
    open: bool = False
    isUnlock: bool = False

    @model_validator(mode="before")
    @classmethod
    def validate_depending_on_unlock(cls, data):
        """根据 isUnlock 状态预处理数据"""
        if isinstance(data, dict):
            if not data.get("isUnlock", False):
                # 创建一个新的数据字典，只保留基本字段
                new_data = {"isUnlock": False, "open": data.get("open", False)}

                # 将 areaId 和 areaName 设置为 None
                new_data["areaId"] = None
                new_data["areaName"] = None

                # 创建一个空的 challengeInfo 字典
                new_data["challengeInfo"] = {}

                return new_data

        return data


class ExploreItem(BaseModel):
    name: str
    progress: int
    type: int


class AreaInfo(BaseModel):
    areaId: int
    areaName: str
    areaProgress: int
    itemList: list[ExploreItem]


class ExploreCountry(BaseModel):
    countryId: int
    countryName: str
    detailPageFontColor: str
    detailPagePic: str
    detailPageProgressColor: str
    homePageIcon: str


class ExploreArea(BaseModel):
    areaInfoList: list[AreaInfo] | None = None
    country: ExploreCountry
    countryProgress: str


class ExploreList(BaseModel):
    """探索度"""

    exploreList: list[ExploreArea] | None = None
    open: bool


class OnlineWeapon(BaseModel):
    """
    {
        "weaponId": 21010011,
        "weaponName": "教学长刃",
        "weaponType": 1,
        "weaponStarLevel": 1,
        "weaponIcon": "https://web-static.kurobbs.com/adminConfig/29/weapon_icon/1716031228478.png",
        "isPreview": false,
        "isNew": false,
        "priority": 1,
        "acronym": "jxcr"
    }
    """

    weaponId: int
    weaponName: str
    weaponType: int
    weaponStarLevel: int
    weaponIcon: str
    isPreview: bool
    isNew: bool
    priority: int
    acronym: str


class OnlineWeaponList(RootModel[list[OnlineWeapon]]):
    def __iter__(self):
        return iter(self.root)


class OnlineRole(BaseModel):
    """
    {
        'roleId': 1608,
        'roleName': '弗洛洛',
        'roleIconUrl': 'https://web-static.kurobbs.com/adminConfig/98/role_icon/1753068445260.png',
        'starLevel': 5,
        'attributeId': 6,
        'weaponTypeId': 5,
        'weaponTypeName': '音感仪',
        'acronym': 'fll',
        'isPreview': False,
        'isNew': False,
        'priority': 285,
        'rolePicture': 'https://web-static.kurobbs.com/adminConfig/98/rolePicture/',
        'rolePictureSmall': 'https://web-static.kurobbs.com/adminConfig/98/rolePictureSmall/',
        'commonSkillList': [{'type': '常态攻击', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/36/role_skill_icon/1753085716584.png', 'recommend': False}, {'type': '共鸣技能', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/36/role_skill_icon/1753085063395.png', 'recommend': False}, {'type': '共鸣解放', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/36/role_skill_icon/1753085554763.png', 'recommend': False}, {'type': '变奏技能', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/36/role_skill_icon/1753085560200.png', 'recommend': False}, {'type': '共鸣回路', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/36/role_skill_icon/1753085704555.png', 'recommend': False}, {'type': '延奏技能', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/36/role_skill_icon/1753085353417.png', 'recommend': False}], 'advanceSkillList': [{'location': '2-1', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068073796.png'}, {'location': '2-2', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068161957.png'}, {'location': '2-3', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068592556.png'}, {'location': '2-4', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753067972012.png'}, {'location': '2-5', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068637999.png'}, {'location': '3-1', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068562194.png'}, {'location': '3-2', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753067862690.png'}, {'location': '3-3', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068670842.png'}, {'location': '3-4', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068186045.png'}, {'location': '3-5', 'iconUrl': 'https://web-static.kurobbs.com/adminConfig/99/advance_skill_icon/1753068673636.png'}]
    }
    """

    roleId: int
    roleName: str
    roleIconUrl: str
    starLevel: int
    attributeId: int
    attributeName: str | None = None
    weaponTypeId: int
    weaponTypeName: str
    acronym: str
    isPreview: bool
    isNew: bool
    priority: int


class OnlineRoleList(RootModel[list[OnlineRole]]):
    def __iter__(self):
        return iter(self.root)


class OnlinePhantom(BaseModel):
    """
    {
        "phantomId": 390080005,
        "name": "鸣钟之龟",
        "cost": 4,
        "risk": "海啸级",
        "iconUrl": "https://web-static.kurobbs.com/adminConfig/35/phantom_icon/1716031298428.png",
        "isPreview": false,
        "isNew": false,
        "priority": 104,
        "fetterIds": "8,7",
        "acronym": "mzzg"
    }
    """

    phantomId: int
    name: str
    cost: int
    risk: str
    iconUrl: str
    isPreview: bool
    isNew: bool
    priority: int
    fetterIds: str
    acronym: str


class OnlinePhantomList(RootModel[list[OnlinePhantom]]):
    def __iter__(self):
        return iter(self.root)


class OwnedRoleList(RootModel[list[int]]):
    def __iter__(self):
        return iter(self.root)


class RoleCultivateSkillLevel(BaseModel):
    type: str
    level: int


class RoleCultivateStatus(BaseModel):
    """角色培养状态
    {
        "roleId": 1107,
        "roleName": "珂莱塔",
        "roleLevel": 90,
        "roleBreakLevel": 6,
        "skillLevelList": [{
                "type": "常态攻击",
                "level": 1
        }, {
                "type": "共鸣技能",
                "level": 10
        }, {
                "type": "共鸣解放",
                "level": 10
        }, {
                "type": "变奏技能",
                "level": 6
        }, {
                "type": "共鸣回路",
                "level": 10
        }, {
                "type": "延奏技能",
                "level": 1
        }],
        "skillBreakList": ["2-3", "3-3", "2-1", "2-2", "2-4", "2-5", "3-1", "3-2", "3-4", "3-5"]
    }
    """

    roleId: int
    roleName: str
    roleLevel: int
    roleBreakLevel: int  # 突破等级
    skillLevelList: list[RoleCultivateSkillLevel]
    skillBreakList: list[str]  # 突破技能


class RoleCultivateStatusList(RootModel[list[RoleCultivateStatus]]):
    def __iter__(self):
        return iter(self.root)


class CultivateCost(BaseModel):
    """培养成本
    {
        "id": "2",
        "name": "贝币",
        "iconUrl": "https://web-static.kurobbs.com/gamerdata/calculator/coin.png",
        "num": 4460260,
        "type": 0,
        "quality": 3,
        "isPreview": false
    }
    """

    id: str
    name: str
    iconUrl: str
    num: int
    type: int
    quality: int
    isPreview: bool


class Strategy(BaseModel):
    """攻略"""

    postId: str
    postTitle: str


class RoleCostDetail(BaseModel):
    """角色培养详情"""

    allCost: list[CultivateCost] | None = None
    missingCost: list[CultivateCost] | None = None
    synthetic: list[CultivateCost] | None = None
    missingRoleCost: list[CultivateCost] | None = None
    missingSkillCost: list[CultivateCost] | None = None
    missingWeaponCost: list[CultivateCost] | None = None
    roleId: int
    weaponId: int | None = None
    strategyList: list[Strategy] | None = None
    showStrategy: bool | None = None


class BatchRoleCostResponse(BaseModel):
    """角色培养成本"""

    roleNum: int  # 角色数量
    weaponNum: int  # 武器数量
    # preview: Dict[str, Optional[List[CultivateCost]]]
    costList: list[RoleCostDetail]  # 每个角色的详细花费


class SlashRole(BaseModel):
    iconUrl: str  # 角色头像
    roleId: int  # 角色ID
    level: int | None = 0  # 角色等级
    chain: int | None = 0  # 角色共鸣链


class SlashHalf(BaseModel):
    buffDescription: str  # 描述
    buffIcon: str  # 图标
    buffName: str  # 名称
    buffQuality: int  # 品质
    roleList: list[SlashRole]  # 角色列表
    score: int  # 分数


class SlashChallenge(BaseModel):
    challengeId: int  # 挑战ID
    challengeName: str  # 挑战名称
    halfList: list[SlashHalf] = Field(default_factory=list)  # 半场列表
    rank: str | None = Field(default="")  # 等级
    score: int  # 分数

    def get_rank(self):
        if not self.rank:
            return ""
        return self.rank.lower()


class SlashDifficulty(BaseModel):
    allScore: int  # 总分数
    challengeList: list[SlashChallenge] = Field(default_factory=list)  # 挑战列表
    difficulty: int  # 难度
    difficultyName: str  # 难度名称
    homePageBG: str  # 首页背景
    maxScore: int  # 最大分数
    teamIcon: str  # 团队图标


class SlashDetail(BaseModel):
    """冥海"""

    isUnlock: bool  # 是否解锁
    seasonEndTime: int  # 赛季结束时间
    difficultyList: list[SlashDifficulty] = Field(default_factory=list)  # 难度列表


class Period(BaseModel):
    """资源简报"""

    title: str  # 标题
    index: int  # 索引


class PeriodList(BaseModel):
    """资源简报"""

    weeks: list[Period] = Field(default_factory=list)  # 周报列表
    months: list[Period] = Field(default_factory=list)  # 月报列表
    versions: list[Period] = Field(default_factory=list)  # 版本列表


class PeriodNode(BaseModel):
    type: str
    num: int
    sort: int | None = None


class PeriodResourceItem(BaseModel):
    type: int
    total: int | str
    detail: list[PeriodNode] = Field(default_factory=list)


class PeriodDetail(BaseModel):
    """资源简报详情"""

    totalCoin: int | None = None
    totalStar: int | None = None
    coinList: list[PeriodNode] = Field(default_factory=list)
    starList: list[PeriodNode] = Field(default_factory=list)
    itemList: list[PeriodResourceItem] | None = None
    copyWriting: str | None = None


class PermanentRouge(BaseModel):
    """浸梦海床"""

    maxScore: int  # 最大分数
    score: int  # 分数
    sort: int  # 排序
    title: str  # 标题


class PhantomBattleBadgeItem(BaseModel):
    """激斗！向着荣耀之丘"""

    iconUrl: str  # 图标
    name: str  # 名称
    sort: int  # 排序
    unlock: bool  # 是否解锁


class PhantomBattle(BaseModel):
    """激斗！向着荣耀之丘"""

    badgeList: list[PhantomBattleBadgeItem] = Field(default_factory=list)  # 勋章列表
    badgeNum: int  # 勋章数量
    cardNum: int  # 卡片数量
    exp: int  # 经验
    expLimit: int  # 经验上限
    level: int  # 等级
    levelIcon: str  # 等级图标
    levelName: str  # 等级名称
    maxBadgeNum: int  # 最大勋章数量
    maxCardNum: int  # 最大卡片数量
    sort: int  # 排序
    title: str  # 标题


class MoreActivity(BaseModel):
    """浸梦海床+激斗！向着荣耀之丘"""

    permanentRouge: PermanentRouge  # 浸梦海床
    phantomBattle: PhantomBattle  # 激斗！向着荣耀之丘
