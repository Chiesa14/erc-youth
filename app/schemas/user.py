from pydantic import BaseModel, EmailStr, constr
from enum import Enum
from typing import Optional

class RoleEnum(str, Enum):
    admin = "admin"
    pere = "Père"
    mere = "Mère"
    other = "Other"

class GenderEnum(str, Enum):
    male = "Male"
    female = "Female"

class FamilyCategoryEnum(str, Enum):
    young = "Young"
    mature = "Mature"

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: Optional[str] = None
    gender: GenderEnum
    phone: str
    family_category: Optional[FamilyCategoryEnum] = None
    family_name: Optional[str] = None
    role: RoleEnum
    other: Optional[str] = None
    profile_pic: Optional[str] = None  # Assume frontend sends a URL for now

class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    gender: GenderEnum
    phone: str
    family_id: int
    family_category: Optional[FamilyCategoryEnum] = None
    family_name: Optional[str] = None
    role: RoleEnum
    other: Optional[str]
    biography: Optional[str]
    profile_pic: Optional[str]

    class Config:
        from_attributes = True


class UserOutWithCode(UserOut):
    access_code: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    biography: Optional[str] = None
    other: Optional[str] = None
    profile_pic: Optional[str] = None


class PasswordUpdate(BaseModel):
    new_password: constr(min_length=6)

class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    gender: Optional[GenderEnum] = None
    phone: Optional[str] = None
    family_category: Optional[FamilyCategoryEnum] = None
    family_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    other: Optional[str] = None
    profile_pic: Optional[str] = None
    biography: Optional[str] = None