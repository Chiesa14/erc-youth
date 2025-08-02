# app/schemas/prayer_chain.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import time
from enum import Enum
from app.utils.timestamps import TimestampMixin


class DayEnum(str, Enum):
    monday = "Monday"
    tuesday = "Tuesday"
    wednesday = "Wednesday"
    thursday = "Thursday"
    friday = "Friday"
    saturday = "Saturday"
    sunday = "Sunday"


class ScheduleBase(BaseModel):
    day: DayEnum
    start_time: time
    end_time: time


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    day: Optional[DayEnum] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class ScheduleResponse(ScheduleBase, TimestampMixin):
    id: int
    prayer_chain_id: int

    class Config:
        from_attributes = True


# Family member schema for detailed family information
class FamilyMemberInfo(BaseModel):
    id: int
    full_name: str
    email: str
    gender: str
    phone: str
    role: Optional[str] = None
    other: Optional[str] = None
    profile_pic: Optional[str] = None
    biography: Optional[str] = None


class FamilyDetails(BaseModel):
    id: int
    category: str
    name: str
    pere: Optional[FamilyMemberInfo] = None  # Father
    mere: Optional[FamilyMemberInfo] = None  # Mother
    members: List[FamilyMemberInfo] = []


class PrayerChainBase(BaseModel):
    family_id: int


class PrayerChainCreate(PrayerChainBase):
    schedules: List[ScheduleCreate] = Field(default_factory=list)


class PrayerChainUpdate(BaseModel):
    family_id: Optional[int] = None


class PrayerChainResponse(PrayerChainBase, TimestampMixin):
    id: int
    family_name: str
    family_details: FamilyDetails
    schedules: List[ScheduleResponse]

    class Config:
        from_attributes = True


# Additional schema for bulk schedule validation
class ScheduleCollisionCheck(BaseModel):
    prayer_chain_id: int
    schedules: List[ScheduleCreate]


class ScheduleCollisionResponse(BaseModel):
    has_collision: bool
    collision_details: Optional[List[str]] = None
    valid_schedules: List[ScheduleCreate]
    conflicting_schedules: List[ScheduleCreate]