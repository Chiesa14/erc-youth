from sqlalchemy import Column, Integer, String, Date, Enum as SQLEnum, Text, DateTime
from sqlalchemy.sql import func

from app.db.session import Base
from app.schemas.family_activity import ActivityStatusEnum
from app.schemas.worship_team import ActivityFrequencyEnum

class WorshipTeamActivity(Base):
    __tablename__ = "worship_team_activities"

    id = Column(Integer, primary_key=True, index=True)
    frequency = Column(SQLEnum(ActivityFrequencyEnum), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    schedule_text = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(SQLEnum(ActivityStatusEnum), nullable=False)
    participants = Column(Integer, nullable=True)
    outcome = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorshipTeamMember(Base):
    __tablename__ = "worship_team_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    instrument = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WorshipTeamSong(Base):
    __tablename__ = "worship_team_songs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    category = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
