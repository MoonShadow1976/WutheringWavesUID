from typing import List, Optional, Tuple

from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Relationship, SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import and_, or_
from gsuid_core.utils.database.base_models import with_session

class GroupRankRole(SQLModel, table=True):
    __tablename__ = "wutheringwaves_group_rank_roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="wutheringwaves_group_rank_teams.id")
    
    role_id: int
    role_name: str
    level: int
    chain: int
    icon_url: str
    star_level: int
    
    team: Optional["GroupRankTeam"] = Relationship(back_populates="roles")

class GroupRankTeam(SQLModel, table=True):
    __tablename__ = "wutheringwaves_group_rank_teams"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    record_id: int = Field(foreign_key="wutheringwaves_group_rank_records.id")
    
    team_index: int
    team_score: int
    buff_name: str
    buff_icon: str
    buff_description: str
    buff_quality: int
    
    record: Optional["GroupRankRecord"] = Relationship(back_populates="teams")
    roles: List[GroupRankRole] = Relationship(back_populates="team", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class GroupRankRecord(SQLModel, table=True):
    __tablename__ = "wutheringwaves_group_rank_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    waves_id: str = Field(index=True)
    name: str
    
    # 排行类型: endless (无尽)
    rank_type: str = Field(index=True)
    
    challenge_id: int = Field(index=True)
    challenge_name: str
    
    score: int
    rank_level: str
    
    teams: List[GroupRankTeam] = Relationship(back_populates="record", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    @classmethod
    @with_session
    async def save_record(
        cls, 
        session: AsyncSession, 
        user_id: str, 
        waves_id: str,
        rank_type: str,
        challenge_id: int,
        data: dict
    ) -> "GroupRankRecord":
        """
        保存或更新排行记录
        """
        # 查询是否存在现有记录
        result = await session.execute(
            select(cls).where(
                (cls.waves_id == waves_id)
                & (cls.rank_type == rank_type)
                & (cls.challenge_id == challenge_id)
            )
        )
        existing_record = result.scalar_one_or_none()
        
        if existing_record:
            # 更新基础信息
            existing_record.user_id = user_id  # 更新 user_id 为最新的
            existing_record.name = data.get("name", "")
            existing_record.challenge_name = data.get("challengeName", "")
            existing_record.score = int(data.get("score", 0))
            existing_record.rank_level = data.get("rank", "")
            
            # 清除旧的队伍信息
            await session.execute(delete(GroupRankTeam).where(GroupRankTeam.record_id == existing_record.id))
            
            record = existing_record
        else:
            record = cls(
                user_id=user_id,
                waves_id=waves_id,
                rank_type=rank_type,
                challenge_id=challenge_id,
                name=data.get("name", ""),
                challenge_name=data.get("challengeName", ""),
                score=int(data.get("score", 0)),
                rank_level=data.get("rank", ""),
            )
            session.add(record)
            await session.flush() # 获取ID

        # 添加队伍信息
        half_list = data.get("halfList", [])
        for index, half in enumerate(half_list):
            team = GroupRankTeam(
                record_id=record.id,
                team_index=index,
                team_score=half.get("score", 0),
                buff_name=half.get("buffName", ""),
                buff_icon=half.get("buffIcon", ""),
                buff_description=half.get("buffDescription", ""),
                buff_quality=half.get("buffQuality", 0),
            )
            session.add(team)
            await session.flush() # 获取ID
            
            # 添加角色信息
            for role in half.get("roleList", []):
                role_record = GroupRankRole(
                    team_id=team.id,
                    role_id=role.get("roleId"),
                    role_name=role.get("roleName", ""),
                    level=role.get("level", 0),
                    chain=role.get("chain", 0),
                    icon_url=role.get("iconUrl", ""),
                    star_level=role.get("starLevel", 0),
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
        user_uid_pairs: List[Tuple[str, str]],
        rank_type: str,
        challenge_id: int,
    ) -> List["GroupRankRecord"]:
        """
        获取指定用户群和类型的排行记录，包含关联数据
        """
        if not user_uid_pairs:
            return []
            
        # 使用 or_ 和 and_ 组合查询，避免 tuple_ 在某些数据库下的兼容性问题
        user_conditions = []
        for uid, wid in user_uid_pairs:
            user_conditions.append(and_(cls.user_id == uid, cls.waves_id == wid))
            
        conditions = [
            cls.rank_type == rank_type,
            cls.challenge_id == challenge_id,
            cls.score > 0,  # 过滤掉 0 分记录
            or_(*user_conditions)
        ]
        
        statement = (
            select(cls)
            .where(*conditions)
            .options(selectinload(cls.teams).selectinload(GroupRankTeam.roles))
        )
        result = await session.execute(statement)
        return result.scalars().all()

    @classmethod 
    @with_session
    async def clean_records(cls, session: AsyncSession, rank_type: Optional[str] = None):
        """
        清理记录
        """
        if rank_type:
            await session.execute(delete(cls).where(cls.rank_type == rank_type))
        else:
            await session.execute(delete(cls))
        await session.commit()

    @classmethod
    @with_session
    async def remove_duplicates(cls, session: AsyncSession):
        """
        移除重复数据，保留最新的
        """
        # 获取所有记录
        result = await session.execute(select(cls))
        all_records = result.scalars().all()
        
        # 按 (waves_id, rank_type, challenge_id) 分组
        groups = {}
        for record in all_records:
            key = (record.waves_id, record.rank_type, record.challenge_id)
            if key not in groups:
                groups[key] = []
            groups[key].append(record)
            
        # 找出需要删除的记录
        to_delete = []
        for key, records in groups.items():
            if len(records) > 1:
                # 按 ID 排序，保留最大的（最新的）
                records.sort(key=lambda x: x.id, reverse=True)
                to_delete.extend(records[1:])
                
        # 删除
        for record in to_delete:
            await session.delete(record)
            
        await session.commit()
        return len(to_delete)