from pydantic import BaseModel, EmailStr, constr, model_validator
from enum import Enum
from typing import Optional
from datetime import datetime
from app.utils.timestamps import TimestampMixin

class RoleEnum(str, Enum):
    admin = "admin"
    pere = "Père"
    mere = "Mère"
    church_pastor = "Pastor"
    other = "Other"

class GenderEnum(str, Enum):
    male = "Male"
    female = "Female"

class FamilyCategoryEnum(str, Enum):
    young = "Young"
    mature = "Mature"

class UserCreate(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    deliverance_name: Optional[str] = None
    email: EmailStr
    password: Optional[str] = None
    gender: GenderEnum
    phone: str
    family_id: Optional[int] = None
    family_category: Optional[FamilyCategoryEnum] = None
    family_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    family_role_id: Optional[int] = None
    other: Optional[str] = None
    profile_pic: Optional[str] = None  # Assume frontend sends a URL for now

    @model_validator(mode="after")
    def _validate_names(self):
        if self.full_name and self.full_name.strip():
            return self

        if (self.first_name and self.first_name.strip()) or (self.last_name and self.last_name.strip()):
            return self

        raise ValueError("Either full_name or first_name/last_name is required")

class UserOut(BaseModel, TimestampMixin):  # Now this works since TimestampMixin is not a BaseModel
    id: int
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    deliverance_name: Optional[str] = None
    email: EmailStr
    gender: GenderEnum
    phone: str
    family_id: Optional[int] = None
    family_category: Optional[FamilyCategoryEnum] = None
    family_name: Optional[str] = None
    role: RoleEnum
    family_role_id: Optional[int] = None
    other: Optional[str]
    biography: Optional[str]
    profile_pic: Optional[str]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class UserUpdate(BaseModel):
    biography: Optional[str] = None
    other: Optional[str] = None
    profile_pic: Optional[str] = None

class PasswordUpdate(BaseModel):
    new_password: constr(min_length=6)


class UserActivationRequest(BaseModel):
    user_id: int
    temp_password: str
    new_password: constr(min_length=6)


class UserActivationResponse(BaseModel):
    message: str
    user_id: int


class PasswordResetResponse(BaseModel):
    message: str
    user_id: int

class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    deliverance_name: Optional[str] = None
    email: Optional[EmailStr] = None
    gender: Optional[GenderEnum] = None
    phone: Optional[str] = None
    family_id: Optional[int] = None
    family_category: Optional[FamilyCategoryEnum] = None
    family_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    family_role_id: Optional[int] = None
    other: Optional[str] = None
    profile_pic: Optional[str] = None
    biography: Optional[str] = None