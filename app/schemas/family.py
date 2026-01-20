from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from app.schemas.family_activity import ActivityStatusEnum, ActivityCategoryEnum
from app.schemas.family_member import GraduationModeEnum, EducationLevelEnum
from app.schemas.user import GenderEnum
from app.utils.timestamps import TimestampMixin

class ActivityResponse(BaseModel, TimestampMixin):
    id: int
    date: date
    status: ActivityStatusEnum
    category: ActivityCategoryEnum
    type: str
    description: Optional[str]

    class Config:
        from_attributes = True

class FamilyResponse(BaseModel, TimestampMixin):
    id: int
    name: str
    category: str
    cover_photo: Optional[str] = None  # Path to family cover photo
    pere: Optional[str]
    mere: Optional[str]
    pere_pic: Optional[str] = None
    mere_pic: Optional[str] = None
    members: List[str]
    activities: List[ActivityResponse]
    last_activity_date: Optional[date]

    class Config:
        from_attributes = True

class FamilyCreate(BaseModel):
    name: str
    category: str
    cover_photo: Optional[str] = None

class FamilyUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    cover_photo: Optional[str] = None

class FamilyMemberCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str]
    home_address: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[GenderEnum]
    education_level: Optional[EducationLevelEnum]
    employment_status: Optional[str]
    bcc_class_participation: Optional[bool]
    year_of_graduation: Optional[int]
    graduation_mode: Optional[GraduationModeEnum]
    parental_status: Optional[bool]

class ActivityCreate(BaseModel):
    date: date
    status: ActivityStatusEnum
    category: ActivityCategoryEnum
    type: str
    description: Optional[str]