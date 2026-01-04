from typing import Optional

from pydantic import BaseModel

from app.schemas.user import RoleEnum
from app.utils.timestamps import TimestampMixin


class FamilyRoleCreate(BaseModel):
    name: str
    system_role: RoleEnum = RoleEnum.other


class FamilyRoleUpdate(BaseModel):
    name: Optional[str] = None
    system_role: Optional[RoleEnum] = None


class FamilyRoleOut(BaseModel, TimestampMixin):
    id: int
    name: str
    system_role: RoleEnum

    class Config:
        from_attributes = True
