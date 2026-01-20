from datetime import date as Date
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.schemas.family_activity import ActivityStatusEnum
from app.utils.timestamps import TimestampMixin


class ActivityFrequencyEnum(str, Enum):
    weekly = "Weekly"
    monthly = "Monthly"
    quarterly = "Quarterly"


class WorshipTeamActivityBase(BaseModel):
    frequency: ActivityFrequencyEnum
    type: str
    title: str
    date: Optional[Date] = None
    schedule_text: Optional[str] = None
    location: Optional[str] = None
    status: ActivityStatusEnum
    participants: Optional[int] = None
    outcome: Optional[str] = None


class WorshipTeamActivityCreate(WorshipTeamActivityBase):
    pass


class WorshipTeamActivityUpdate(BaseModel):
    frequency: Optional[ActivityFrequencyEnum] = None
    type: Optional[str] = None
    title: Optional[str] = None
    date: Optional[Date] = None
    schedule_text: Optional[str] = None
    location: Optional[str] = None
    status: Optional[ActivityStatusEnum] = None
    participants: Optional[int] = None
    outcome: Optional[str] = None


class WorshipTeamActivityOut(WorshipTeamActivityBase, TimestampMixin):
    id: int

    class Config:
        from_attributes = True
