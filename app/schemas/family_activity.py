from enum import Enum
from pydantic import BaseModel, computed_field
from datetime import date as Date, time
from typing import Optional
from app.utils.timestamps import TimestampMixin


class ActivityCategoryEnum(str, Enum):
    spiritual = "Spiritual"
    social = "Social"

class SpiritualTypeEnum(str, Enum):
    prayer_calendar = "Prayer calendars"
    overnight = "Overnights"
    crusade = "Crusades"
    agape_event = "Agape events"

class SocialTypeEnum(str, Enum):
    contribution = "Contributions"
    illness = "Illnesses"
    bereavement = "Bereavements"
    wedding = "Weddings"
    transfer = "Transfers"

class ActivityStatusEnum(str, Enum):
    planned = "Planned"
    ongoing = "Ongoing"
    completed = "Completed"
    cancelled = "Cancelled"


class ActivityBase(BaseModel):
    family_id: int
    date: Date
    start_date: Optional[Date] = None
    end_date: Optional[Date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: ActivityStatusEnum
    category: ActivityCategoryEnum
    type: str  # will validate in controller if matches category
    description: Optional[str] = None

class ActivityCreate(BaseModel):
    date: Optional[Date] = None
    start_date: Optional[Date] = None
    end_date: Optional[Date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[ActivityStatusEnum] = None
    category: ActivityCategoryEnum
    type: str                   # Example: 'Prayer calendar', 'Illness', etc.
    description: Optional[str] = None
    family_id: Optional[int] = None

class ActivityUpdate(BaseModel):
    date: Optional[Date] = None
    start_date: Optional[Date] = None
    end_date: Optional[Date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    status: Optional[ActivityStatusEnum] = None
    category: Optional[ActivityCategoryEnum] = None
    type: Optional[str] = None
    description: Optional[str] = None

class ActivityOut(ActivityBase, TimestampMixin):
    id: int
    family_name: str

    @classmethod
    def from_orm(cls, obj):
        # Ensure family_name is populated from the family relationship
        obj.family_name = obj.family.name if obj.family else "Unknown"
        return super().from_orm(obj)