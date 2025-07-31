# app/models/prayer_chain.py
from sqlalchemy import Column, Integer, ForeignKey, String, Time, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.db.session import Base
from enum import Enum


class DayEnum(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"


class PrayerChain(Base):
    __tablename__ = "prayer_chains"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)

    # Relationships
    family = relationship("Family", back_populates="prayer_chains")
    schedules = relationship("Schedule", back_populates="prayer_chain", cascade="all, delete-orphan")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    day = Column(SQLEnum(DayEnum), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    prayer_chain_id = Column(Integer, ForeignKey("prayer_chains.id"), nullable=False)

    # Relationships
    prayer_chain = relationship("PrayerChain", back_populates="schedules")