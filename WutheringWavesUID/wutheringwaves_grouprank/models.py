from typing import Optional

from gsuid_core.utils.database.base_models import with_session
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import and_, or_, text
from sqlmodel import Field, Relationship, SQLModel, select


class GroupRankRole(SQLModel, table=True):
    """群排行中的角色信息"""

    __tablename__ = "ww_rank_role"

    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="ww_rank_team.id", description="所属队伍ID")

    role_id: int = Field(description="角色ID")
    level: int = Field(description="角色等级")
    chain: int = Field(description="角色共鸣链")

    team: Optional["GroupRankTeam"] = Relationship(back_populates="roles")


class GroupRankTeam(SQLModel, table=True):
    """群排行中的队伍信息"""

    __tablename__ = "ww_rank_team"

    id: int | None = Field(default=None, primary_key=True)
    record_id: int = Field(foreign_key="ww_rank_record.id", description="所属记录ID")

    team_index: int = Field(description="队伍索引（0或1）")
    team_score: int = Field(description="队伍得分")
    buff_id: int = Field(description="队伍选择的增益ID")

    record: Optional["GroupRankRecord"] = Relationship(back_populates="teams")
    roles: list[GroupRankRole] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class GroupRankRecord(SQLModel, table=True):
    __tablename__ = "ww_rank_record"

    """群排行总记录"""

    __tablename__ = "ww_rank_record"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, description="GSUID用户ID")
    waves_id: str = Field(index=True, description="鸣潮游戏UID")
    name: str = Field(description="玩家昵称")

    rank_type: str = Field(index=True, description="排行类型 (例如 'endless')")
    season_id: int = Field(index=True, description="赛季ID (通常是结束时间的时间戳)")
    challenge_id: int = Field(index=True, description="挑战ID")

    score: int = Field(description="总得分")
    rank_level: str = Field(description="评级 (例如 'S')")

    teams: list[GroupRankTeam] = Relationship(back_populates="record", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

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

        # 构建用户查询条件
        user_conditions = []
        for uid, wid in user_uid_pairs:
            user_conditions.append(and_(cls.user_id == uid, cls.waves_id == wid))

        # 构建总查询条件
        conditions = [
            cls.rank_type == rank_type,
            cls.season_id == season_id,
            cls.challenge_id == challenge_id,
            cls.score > 0,  # 只查询有分数的记录
            or_(*user_conditions),
        ]

        statement = (
            select(cls)
            .where(*conditions)
            .options(selectinload(cls.teams).selectinload(GroupRankTeam.roles))  # 预加载队伍和角色信息
        )
        result = await session.execute(statement)
        return result.scalars().all()

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
