from typing import Optional

from gsuid_core.utils.database.base_models import with_session
from gsuid_core.utils.database.startup import exec_list
from sqlalchemy import delete, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import text
from sqlmodel import Field, Relationship, SQLModel, select

exec_list.extend(
    [
        "ALTER TABLE ww_rank_team ADD COLUMN buff_quality INTEGER DEFAULT 3",
        # 练度排行新增字段
        "ALTER TABLE ww_rank_record ADD COLUMN train_score REAL DEFAULT 0.0",
        "ALTER TABLE ww_rank_role ADD COLUMN record_id INTEGER",
        "ALTER TABLE ww_rank_role ADD COLUMN train_score REAL DEFAULT 0.0",
    ]
)


class GroupRankRole(SQLModel, table=True):
    """群排行中的角色信息"""

    __tablename__ = "ww_rank_role"

    id: int | None = Field(default=None, primary_key=True)
    team_id: int | None = Field(default=None, foreign_key="ww_rank_team.id", description="所属队伍ID（无尽排行使用）")
    record_id: int | None = Field(default=None, foreign_key="ww_rank_record.id", description="所属记录ID（练度排行使用）")

    role_id: int = Field(description="角色ID")
    level: int = Field(default=0, description="角色等级")
    chain: int = Field(default=0, description="角色共鸣链")
    train_score: float = Field(default=0.0, description="角色练度分数")

    team: Optional["GroupRankTeam"] = Relationship(back_populates="roles")
    record: Optional["GroupRankRecord"] = Relationship(back_populates="train_roles")


class GroupRankTeam(SQLModel, table=True):
    """群排行中的队伍信息"""

    __tablename__ = "ww_rank_team"

    id: int | None = Field(default=None, primary_key=True)
    record_id: int = Field(foreign_key="ww_rank_record.id", description="所属记录ID")

    team_index: int = Field(description="队伍索引（0或1）")
    team_score: int = Field(description="队伍得分")
    buff_id: int = Field(description="队伍选择的增益ID")
    buff_quality: int = Field(default=3, description="队伍选择的增益品质")

    record: Optional["GroupRankRecord"] = Relationship(back_populates="teams")
    roles: list[GroupRankRole] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class GroupRankRecord(SQLModel, table=True):
    """群排行总记录"""

    __tablename__ = "ww_rank_record"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, description="GSUID用户ID")
    waves_id: str = Field(index=True, description="鸣潮游戏UID")
    name: str = Field(default="", description="玩家昵称")

    rank_type: str = Field(index=True, description="排行类型 (endless/train)")
    season_id: int = Field(default=0, index=True, description="赛季ID (通常是结束时间的时间戳)")
    challenge_id: int = Field(default=0, index=True, description="挑战ID")

    score: int = Field(default=0, description="无尽排行总得分")
    train_score: float = Field(default=0.0, description="练度总分")
    rank_level: str = Field(default="", description="评级 (例如 'S')")

    teams: list[GroupRankTeam] = Relationship(back_populates="record", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    train_roles: list[GroupRankRole] = Relationship(
        back_populates="record",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "foreign_keys": "[GroupRankRole.record_id]",
        },
    )

    @classmethod
    @with_session
    async def save_record(
        cls,
        session: AsyncSession,
        user_id: str,
        waves_id: str,
        rank_type: str,
        season_id: int,
        challenge_id: int,
        data: dict,
    ) -> "GroupRankRecord":
        """保存或更新一条完整的排行记录，包括队伍和角色信息"""
        result = await session.execute(
            select(cls).where(
                (cls.waves_id == waves_id)
                & (cls.rank_type == rank_type)
                & (cls.season_id == season_id)
                & (cls.challenge_id == challenge_id)
            )
        )
        existing_record = result.scalar_one_or_none()

        if existing_record:
            # 如果记录已存在，则更新
            existing_record.user_id = user_id
            existing_record.name = data.get("name", "")
            existing_record.score = int(data.get("score", 0))
            existing_record.rank_level = data.get("rank", "")
            # 删除旧的队伍信息以便重新创建
            await session.execute(delete(GroupRankTeam).where(GroupRankTeam.record_id == existing_record.id))
            record = existing_record
        else:
            # 如果记录不存在，则创建新记录
            record = cls(
                user_id=user_id,
                waves_id=waves_id,
                rank_type=rank_type,
                season_id=season_id,
                challenge_id=challenge_id,
                name=data.get("name", ""),
                score=int(data.get("score", 0)),
                rank_level=data.get("rank", ""),
            )
            session.add(record)
            await session.flush()  # 刷新以获取 record.id

        # 创建新的队伍和角色信息
        half_list = data.get("halfList", [])
        for index, half in enumerate(half_list):
            team = GroupRankTeam(
                record_id=record.id,
                team_index=index,
                team_score=half.get("score", 0),
                buff_id=half.get("buff_id", 0),
                buff_quality=half.get("buff_quality", 3),
            )
            session.add(team)
            await session.flush()  # 刷新以获取 team.id

            for role in half.get("roleList", []):
                role_record = GroupRankRole(
                    team_id=team.id,
                    role_id=role.get("roleId"),
                    level=role.get("level", 0),
                    chain=role.get("chain", 0),
                )
                session.add(role_record)

        await session.commit()
        await session.refresh(record)
        return record

    @classmethod
    @with_session
    async def get_group_records(
        cls,
        session: AsyncSession,
        user_uid_pairs: list[tuple[str, str]],
        rank_type: str,
        season_id: int,
        challenge_id: int,
    ) -> list["GroupRankRecord"]:
        """获取指定群组、赛季和挑战的排行记录"""
        if not user_uid_pairs:
            return []

        results = []
        # 分批查询，避免 SQLite 参数过多或表达式树过深
        batch_size = 500
        for i in range(0, len(user_uid_pairs), batch_size):
            batch_pairs = user_uid_pairs[i : i + batch_size]

            # 构建总查询条件
            conditions = [
                cls.rank_type == rank_type,
                cls.season_id == season_id,
                cls.challenge_id == challenge_id,
                cls.score > 0,  # 只查询有分数的记录
                tuple_(cls.user_id, cls.waves_id).in_(batch_pairs),
            ]

            statement = (
                select(cls)
                .where(*conditions)
                .options(selectinload(cls.teams).selectinload(GroupRankTeam.roles))  # 预加载队伍和角色信息
            )
            result = await session.execute(statement)
            results.extend(result.scalars().all())

        return results

    @classmethod
    @with_session
    async def clean_records(
        cls,
        session: AsyncSession,
        rank_type: str | None = None,
        season_id: int | None = None,
    ):
        """清理指定排行类型或赛季的记录"""
        query = delete(cls)
        if rank_type:
            query = query.where(cls.rank_type == rank_type)
        if season_id:
            query = query.where(cls.season_id == season_id)
        await session.execute(query)
        await session.commit()

    @classmethod
    @with_session
    async def get_all_season_ids(cls, session: AsyncSession, rank_type: str) -> list[int]:
        """获取指定排行类型的所有赛季ID"""
        result = await session.execute(select(cls.season_id).where(cls.rank_type == rank_type).distinct())
        return result.scalars().all()

    @classmethod
    @with_session
    async def clean_old_seasons(cls, session: AsyncSession, rank_type: str):
        """清理旧赛季数据，只保留最近的两个赛季"""
        result = await session.execute(select(cls.season_id).where(cls.rank_type == rank_type).distinct())
        all_season_ids = result.scalars().all()
        if len(all_season_ids) > 2:
            all_season_ids.sort()
            ids_to_delete = all_season_ids[:-2]  # 保留最新的两个
            await session.execute(
                delete(cls).where(
                    cls.rank_type == rank_type,
                    cls.season_id.in_(ids_to_delete),
                )
            )
            await session.commit()

    @classmethod
    @with_session
    async def drop_old_tables(cls, session: AsyncSession):
        """删除旧的、已弃用的排行榜相关表（用于版本迁移）"""
        tables_to_drop = [
            "wutheringwaves_group_rank_records",
            "wutheringwaves_group_rank_roles",
            "wutheringwaves_group_rank_teams",
        ]
        for table in tables_to_drop:
            await session.execute(text(f"DROP TABLE IF EXISTS {table};"))
        await session.commit()

    # ==================== 练度排行相关方法 ====================

    @classmethod
    @with_session
    async def save_train_record(
        cls,
        session: AsyncSession,
        user_id: str,
        waves_id: str,
        name: str,
        train_score: float,
        char_scores: list[dict],
    ) -> "GroupRankRecord":
        """
        保存或更新练度排行记录

        Args:
            user_id: GSUID用户ID
            waves_id: 鸣潮游戏UID
            name: 玩家昵称
            train_score: 练度总分
            char_scores: 角色分数列表，格式为 [{"role_id": int, "score": float}, ...]
        """
        # 查找现有记录
        result = await session.execute(select(cls).where((cls.waves_id == waves_id) & (cls.rank_type == "train")))
        existing_record = result.scalar_one_or_none()

        if existing_record:
            # 更新现有记录
            existing_record.user_id = user_id
            existing_record.name = name
            existing_record.train_score = train_score
            # 删除旧的角色分数记录
            await session.execute(delete(GroupRankRole).where(GroupRankRole.record_id == existing_record.id))
            record = existing_record
        else:
            # 创建新记录
            record = cls(
                user_id=user_id,
                waves_id=waves_id,
                name=name,
                rank_type="train",
                train_score=train_score,
            )
            session.add(record)
            await session.flush()

        # 创建角色分数记录
        # 注意：由于现有数据库中 team_id 有 NOT NULL 约束，我们使用 0 作为占位值
        # 表示该角色记录属于练度排行而非无尽排行
        for char in char_scores:
            role_record = GroupRankRole(
                team_id=0,  # 使用 0 作为占位值，表示练度排行（无队伍）
                record_id=record.id,
                role_id=char.get("role_id", 0),
                train_score=char.get("score", 0.0),
            )
            session.add(role_record)

        await session.commit()
        await session.refresh(record)
        return record

    @classmethod
    @with_session
    async def get_train_records(
        cls,
        session: AsyncSession,
        user_uid_pairs: list[tuple[str, str]],
    ) -> list["GroupRankRecord"]:
        """
        获取指定用户的练度排行记录

        Args:
            user_uid_pairs: 用户ID和游戏UID的元组列表
        """
        if not user_uid_pairs:
            return []

        results = []
        batch_size = 500
        for i in range(0, len(user_uid_pairs), batch_size):
            batch_pairs = user_uid_pairs[i : i + batch_size]

            conditions = [
                cls.rank_type == "train",
                cls.train_score > 0,
                tuple_(cls.user_id, cls.waves_id).in_(batch_pairs),
            ]

            statement = select(cls).where(*conditions).options(selectinload(cls.train_roles))
            result = await session.execute(statement)
            results.extend(result.scalars().all())

        return results

    @classmethod
    @with_session
    async def get_train_record_by_waves_id(
        cls,
        session: AsyncSession,
        waves_id: str,
    ) -> Optional["GroupRankRecord"]:
        """根据 waves_id 获取练度排行记录"""
        result = await session.execute(
            select(cls).where((cls.waves_id == waves_id) & (cls.rank_type == "train")).options(selectinload(cls.train_roles))
        )
        return result.scalar_one_or_none()
