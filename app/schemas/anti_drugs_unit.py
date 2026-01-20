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


class AntiDrugsActivityBase(BaseModel):
    frequency: ActivityFrequencyEnum
    type: str
    title: str
    date: Optional[Date] = None
    schedule_text: Optional[str] = None
    location: Optional[str] = None
    status: ActivityStatusEnum
    participants: Optional[int] = None


class AntiDrugsActivityCreate(AntiDrugsActivityBase):
    pass


class AntiDrugsActivityUpdate(BaseModel):
    frequency: Optional[ActivityFrequencyEnum] = None
    type: Optional[str] = None
    title: Optional[str] = None
    date: Optional[Date] = None
    schedule_text: Optional[str] = None
    location: Optional[str] = None
    status: Optional[ActivityStatusEnum] = None
    participants: Optional[int] = None


class AntiDrugsActivityOut(AntiDrugsActivityBase, TimestampMixin):
    id: int

    class Config:
        from_attributes = True


class AntiDrugsTestimonyBase(BaseModel):
    name: str
    story: str
    date: Optional[Date] = None
    is_anonymous: bool = False


class AntiDrugsTestimonyCreate(AntiDrugsTestimonyBase):
    pass


class AntiDrugsTestimonyUpdate(BaseModel):
    name: Optional[str] = None
    story: Optional[str] = None
    date: Optional[Date] = None
    is_anonymous: Optional[bool] = None


class AntiDrugsTestimonyOut(AntiDrugsTestimonyBase, TimestampMixin):
    id: int

    class Config:
        from_attributes = True


class AntiDrugsOutreachPlanBase(BaseModel):
    title: str
    description: str
    target: Optional[str] = None
    status: str
    type: Optional[str] = None


class AntiDrugsOutreachPlanCreate(AntiDrugsOutreachPlanBase):
    pass


class AntiDrugsOutreachPlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    target: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None


class AntiDrugsOutreachPlanOut(AntiDrugsOutreachPlanBase, TimestampMixin):
    id: int

    class Config:
        from_attributes = True
