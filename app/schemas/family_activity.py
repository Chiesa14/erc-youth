from enum import Enum
from pydantic import BaseModel
from datetime import date
from typing import Optional


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
    date: date
    status: ActivityStatusEnum
    category: ActivityCategoryEnum
    type: str  # will validate in controller if matches category
    description: Optional[str] = None

class ActivityCreate(BaseModel):
    date: date
    status: ActivityStatusEnum  # Example: 'planned', 'completed'
    category: ActivityCategoryEnum
    type: str                   # Example: 'Prayer calendar', 'Illness', etc.
    description: Optional[str]
    family_id: Optional[int] = None

class ActivityUpdate(BaseModel):
    date: Optional[date]
    status: Optional[ActivityStatusEnum]
    category: Optional[ActivityCategoryEnum]
    type: Optional[str]
    description: Optional[str]

class ActivityOut(ActivityBase):
    id: int

    class Config:
        from_attributes = True
