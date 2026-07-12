import json
from typing import Optional

from gsuid_core.utils.database.base_models import with_session
from gsuid_core.utils.database.startup import exec_list
from sqlalchemy import delete
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
        # 矩阵排行新增字段
        "ALTER TABLE ww_rank_record ADD COLUMN version TEXT DEFAULT NULL",
        "ALTER TABLE ww_rank_record ADD COLUMN team_count INTEGER DEFAULT 0",
        "ALTER TABLE ww_rank_record ADD COLUMN team_score INTEGER DEFAULT 0",
        "ALTER TABLE ww_rank_team ADD COLUMN buff_icon TEXT DEFAULT ''",
        # 抽卡排行新增字段
        "ALTER TABLE ww_rank_record ADD COLUMN gacha_data TEXT DEFAULT NULL",
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

    buff_icon: str = Field(default="", description="增益图标URL（矩阵专用）")

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

    version: str | None = Field(default=None, index=True, description="矩阵排行版本号（如'2.4'）")
    team_count: int = Field(default=0, description="矩阵队伍总数")
    team_score: int = Field(default=0, description="矩阵最高队伍分数")

    gacha_data: str | None = Field(default=None, description="抽卡统计数据（JSON格式）")

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
        uid_lists: list[str],
        rank_type: str,
        season_id: int,
        challenge_id: int,
    ) -> list["GroupRankRecord"]:
        """获取指定群组、赛季和挑战的排行记录"""
        if not uid_lists:
            return []

        results = []
        # 分批查询，避免 SQLite 参数过多或表达式树过深
        batch_size = 500
        for i in range(0, len(uid_lists), batch_size):
            batch_pairs = uid_lists[i : i + batch_size]

            # 构建总查询条件
            conditions = [
                cls.rank_type == rank_type,
                cls.season_id == season_id,
                cls.challenge_id == challenge_id,
                cls.score > 0,  # 只查询有分数的记录
                cls.waves_id.in_(batch_pairs),
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
        """清理指定排行类型或赛季的记录（同时删除关联子表）"""
        # 构建查询条件，获取要删除的记录ID
        conditions = []
        if rank_type:
            conditions.append(cls.rank_type == rank_type)
        if season_id is not None:
            conditions.append(cls.season_id == season_id)

        # 如果没有条件，则删除所有（危险，但保留原行为）
        stmt = select(cls.id).where(*conditions) if conditions else select(cls.id)
        result = await session.execute(stmt)
        record_ids = result.scalars().all()

        if not record_ids:
            return

        # 1. 删除直接关联的角色记录（train_roles，即 record_id 关联的）
        await session.execute(delete(GroupRankRole).where(GroupRankRole.record_id.in_(record_ids)))

        # 2. 删除队伍记录（同时会级联删除其角色，但使用 execute 不会触发 ORM 级联，
        #    所以需要先删除角色，再删除队伍。上面已删除 record_id 关联的角色，
        #    但队伍关联的角色（team_id）还未删除，需再删一次）
        #    先查出这些队伍关联的角色（通过 team_id 关联）
        team_subquery = select(GroupRankTeam.id).where(GroupRankTeam.record_id.in_(record_ids))
        await session.execute(delete(GroupRankRole).where(GroupRankRole.team_id.in_(team_subquery)))

        # 3. 删除队伍
        await session.execute(delete(GroupRankTeam).where(GroupRankTeam.record_id.in_(record_ids)))

        # 4. 删除主表记录
        await session.execute(delete(cls).where(cls.id.in_(record_ids)))

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
        """清理旧赛季数据，只保留最近的两个赛季（用于无尽排行）"""
        # 获取所有赛季ID
        result = await session.execute(select(cls.season_id).where(cls.rank_type == rank_type).distinct())
        all_season_ids = result.scalars().all()

        if len(all_season_ids) <= 2:
            return

        all_season_ids.sort()
        ids_to_delete = all_season_ids[:-2]  # 保留最新的两个

        # 获取这些赛季对应的记录ID
        rec_result = await session.execute(select(cls.id).where(cls.rank_type == rank_type, cls.season_id.in_(ids_to_delete)))
        record_ids = rec_result.scalars().all()

        if not record_ids:
            return

        # 删除关联数据（同 clean_records）
        await session.execute(delete(GroupRankRole).where(GroupRankRole.record_id.in_(record_ids)))
        team_subquery = select(GroupRankTeam.id).where(GroupRankTeam.record_id.in_(record_ids))
        await session.execute(delete(GroupRankRole).where(GroupRankRole.team_id.in_(team_subquery)))
        await session.execute(delete(GroupRankTeam).where(GroupRankTeam.record_id.in_(record_ids)))
        await session.execute(delete(cls).where(cls.id.in_(record_ids)))

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
        uid_lists: list[str],
    ) -> list["GroupRankRecord"]:
        """
        获取指定用户的练度排行记录

        Args:
            uid_lists: 游戏UID的列表
        """
        if not uid_lists:
            return []

        results = []
        batch_size = 500
        for i in range(0, len(uid_lists), batch_size):
            batch_pairs = uid_lists[i : i + batch_size]

            conditions = [
                cls.rank_type == "train",
                cls.train_score > 0,
                cls.waves_id.in_(batch_pairs),
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

    # ==================== 矩阵排行模型 ====================

    @classmethod
    @with_session
    async def save_matrix_record(
        cls,
        session: AsyncSession,
        user_id: str,
        waves_id: str,
        name: str,
        version: str,
        total_score: int,
        team_count: int,
        team_score: int,
        buff_icon: str,
        char_scores: list[dict],  # [{"role_id": int, "chain": int}, ...]
    ) -> "GroupRankRecord":
        """
        保存或更新矩阵排行记录（按 waves_id + version 去重）
        创建一条队伍记录（team_index=0），并填充角色信息
        """
        # 查询现有记录
        result = await session.execute(
            select(cls).where((cls.waves_id == waves_id) & (cls.rank_type == "matrix") & (cls.version == version))
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.user_id = user_id
            existing.name = name
            existing.total_score = total_score  # 注意：total_score 应映射到 score 字段
            existing.team_count = team_count
            existing.team_score = team_score
            # 删除旧的队伍和角色（因为角色通过队伍级联删除）
            await session.execute(delete(GroupRankTeam).where(GroupRankTeam.record_id == existing.id))
            record = existing
        else:
            record = cls(
                user_id=user_id,
                waves_id=waves_id,
                name=name,
                rank_type="matrix",
                version=version,
                score=total_score,  # 使用 score 存储总得分
                team_count=team_count,
                team_score=team_score,
            )
            session.add(record)
            await session.flush()  # 获取 record.id

        # 创建队伍记录（仅一个队伍，代表最高分队伍）
        team = GroupRankTeam(
            record_id=record.id,
            team_index=0,
            team_score=team_score,
            buff_id=0,
            buff_quality=0,
            buff_icon=buff_icon,
        )
        session.add(team)
        await session.flush()  # 获取 team.id

        # 创建角色记录
        for char in char_scores:
            role = GroupRankRole(
                team_id=team.id,
                role_id=char.get("role_id", 0),
                chain=char.get("chain", 0),
                level=0,  # 矩阵无等级，默认0
            )
            session.add(role)

        await session.commit()
        await session.refresh(record)
        return record

    @classmethod
    @with_session
    async def get_matrix_records(
        cls,
        session: AsyncSession,
        waves_ids: list[str],
        version: str,
    ) -> list["GroupRankRecord"]:
        """获取指定用户列表和版本的矩阵排行记录（已按总分排序）"""
        if not waves_ids:
            return []

        results = []
        batch_size = 500
        for i in range(0, len(waves_ids), batch_size):
            batch = waves_ids[i : i + batch_size]
            stmt = (
                select(cls)
                .where(
                    cls.waves_id.in_(batch),
                    cls.rank_type == "matrix",
                    cls.version == version,
                    cls.score > 0,
                )
                .options(selectinload(cls.teams).selectinload(GroupRankTeam.roles))
                .order_by(cls.score.desc())
            )
            result = await session.execute(stmt)
            results.extend(result.scalars().all())
        return results

    @classmethod
    @with_session
    async def get_all_matrix_versions(cls, session: AsyncSession) -> list[str]:
        """获取所有已记录的矩阵版本号"""
        result = await session.execute(select(cls.version).where(cls.rank_type == "matrix").distinct())
        versions = result.scalars().all()
        return [v for v in versions if v is not None]  # 保证返回列表

    @classmethod
    @with_session
    async def clean_old_matrix_versions(cls, session: AsyncSession):
        """清理旧版本矩阵数据，只保留最近两个版本"""
        # 获取所有版本
        result = await session.execute(select(cls.version).where(cls.rank_type == "matrix").distinct())
        versions = result.scalars().all()
        versions = [v for v in versions if v is not None]

        if len(versions) <= 2:
            return

        sorted_versions = sorted(versions)
        to_delete = sorted_versions[:-2]

        # 获取这些版本对应的记录ID
        rec_result = await session.execute(select(cls.id).where(cls.rank_type == "matrix", cls.version.in_(to_delete)))
        record_ids = rec_result.scalars().all()

        if not record_ids:
            return

        # 删除关联数据（同 clean_records）
        await session.execute(delete(GroupRankRole).where(GroupRankRole.record_id.in_(record_ids)))
        team_subquery = select(GroupRankTeam.id).where(GroupRankTeam.record_id.in_(record_ids))
        await session.execute(delete(GroupRankRole).where(GroupRankRole.team_id.in_(team_subquery)))
        await session.execute(delete(GroupRankTeam).where(GroupRankTeam.record_id.in_(record_ids)))
        await session.execute(delete(cls).where(cls.id.in_(record_ids)))

        await session.commit()

    # ==================== 抽卡排行 ====================

    @classmethod
    @with_session
    async def save_gacha_record(
        cls,
        session: AsyncSession,
        user_id: str,
        waves_id: str,
        name: str,
        gacha_stats: dict,
    ) -> "GroupRankRecord":
        """保存或更新抽卡记录（按 waves_id 唯一，rank_type='gacha'）"""
        # 查找是否存在
        result = await session.execute(select(cls).where((cls.waves_id == waves_id) & (cls.rank_type == "gacha")))
        existing = result.scalar_one_or_none()

        if existing:
            existing.user_id = user_id
            existing.name = name
            existing.gacha_data = json.dumps(gacha_stats, ensure_ascii=False)
            record = existing
        else:
            record = cls(
                user_id=user_id,
                waves_id=waves_id,
                name=name,
                rank_type="gacha",
                gacha_data=json.dumps(gacha_stats, ensure_ascii=False),
                # 其他字段设默认值（避免 NOT NULL 约束错误）
                season_id=0,
                challenge_id=0,
                score=0,
                train_score=0.0,
                rank_level="",
                version=None,
                team_count=0,
                team_score=0,
            )
            session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    @classmethod
    @with_session
    async def get_gacha_record(
        cls,
        session: AsyncSession,
        waves_id: str,
    ) -> Optional["GroupRankRecord"]:
        """获取用户的抽卡记录"""
        result = await session.execute(select(cls).where((cls.waves_id == waves_id) & (cls.rank_type == "gacha")))
        return result.scalar_one_or_none()

    @classmethod
    @with_session
    async def get_gacha_records_by_waves_ids(
        cls,
        session: AsyncSession,
        waves_ids: list[str],
    ) -> list["GroupRankRecord"]:
        """批量获取指定 waves_id 的抽卡记录（rank_type='gacha'）"""
        if not waves_ids:
            return []
        results = []
        batch_size = 500
        for i in range(0, len(waves_ids), batch_size):
            batch = waves_ids[i : i + batch_size]
            stmt = select(cls).where(cls.waves_id.in_(batch), cls.rank_type == "gacha")
            result = await session.execute(stmt)
            results.extend(result.scalars().all())
        return results
