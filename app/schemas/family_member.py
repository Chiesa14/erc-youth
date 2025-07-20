from pydantic import BaseModel, EmailStr, field_serializer, computed_field
from typing import Optional, List
from datetime import date
from enum import Enum

from app.schemas.user import GenderEnum

class AccessPermissionEnum(str, Enum):
    submit_reports = "submit_reports"
    view_activities = "view_activities"
    upload_documents = "upload_documents"
    manage_calendar = "manage_calendar"

class DelegatedAccessOut(BaseModel):
    member_id: int
    name: str
    permissions: List[AccessPermissionEnum]

class GrantAccessRequest(BaseModel):
    member_id: int
    permissions: List[AccessPermissionEnum]

class EducationLevelEnum(str, Enum):
    none = "None"
    primary = "Primary"
    secondary = "Secondary"
    tertiary = "Tertiary"
    other = "Other"

class EmploymentStatusEnum(str, Enum):
    employed = "Employed"
    unemployed = "Unemployed"
    student = "Student"
    retired = "Retired"
    other = "Other"

class GraduationModeEnum(str, Enum):
    online = "Online"
    physical = "Physical"

class FamilyMemberBase(BaseModel):
    name: str
    phone: str  # required
    email: Optional[EmailStr] = None  # optional
    home_address: Optional[str] = None
    date_of_birth: date
    gender: GenderEnum
    education_level: Optional[str] = None
    employment_status: Optional[str] = None
    bcc_class_participation: Optional[bool] = None
    year_of_graduation: Optional[int] = None
    graduation_mode: Optional[GraduationModeEnum] = None
    parental_status: bool
    family_id: Optional[int] = None

class FamilyMemberCreate(FamilyMemberBase):
    family_id: Optional[int]= None

class FamilyMemberUpdate(FamilyMemberBase):
    pass

class FamilyMemberOut(FamilyMemberBase):
    id: int
    family_id: int

    class Config:
        from_attributes = True

    @computed_field
    def age(self) -> int:
        today = date.today()
        return (
            today.year - self.date_of_birth.year -
            ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )