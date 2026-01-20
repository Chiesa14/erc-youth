from sqlalchemy import Column, Integer, String, Date, Enum as SQLEnum, Boolean, Text, DateTime
from sqlalchemy.sql import func

from app.db.session import Base
from app.schemas.family_activity import ActivityStatusEnum
from app.schemas.anti_drugs_unit import ActivityFrequencyEnum

class AntiDrugsActivity(Base):
    __tablename__ = "anti_drugs_activities"

    id = Column(Integer, primary_key=True, index=True)
    frequency = Column(SQLEnum(ActivityFrequencyEnum), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    date = Column(Date, nullable=True)
    schedule_text = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(SQLEnum(ActivityStatusEnum), nullable=False)
    participants = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AntiDrugsTestimony(Base):
    __tablename__ = "anti_drugs_testimonies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    story = Column(Text, nullable=False)
    date = Column(Date, nullable=True)
    is_anonymous = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AntiDrugsOutreachPlan(Base):
    __tablename__ = "anti_drugs_outreach_plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    target = Column(String, nullable=True)
    status = Column(String, nullable=False)
    type = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
