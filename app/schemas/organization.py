from typing import Optional, List

from pydantic import BaseModel

from app.models.organization import OrgLevelEnum
from app.utils.timestamps import TimestampMixin


class OrganizationPositionBase(BaseModel):
    level: OrgLevelEnum
    name: str
    id_name: Optional[str] = None
    role: str
    position: str
    photo: Optional[str] = None
    sort_order: Optional[int] = None


class OrganizationPositionCreate(OrganizationPositionBase):
    pass


class OrganizationPositionUpdate(BaseModel):
    level: Optional[OrgLevelEnum] = None
    name: Optional[str] = None
    id_name: Optional[str] = None
    role: Optional[str] = None
    position: Optional[str] = None
    photo: Optional[str] = None
    sort_order: Optional[int] = None


class OrganizationPositionOut(OrganizationPositionBase, TimestampMixin):
    id: int

    class Config:
        from_attributes = True


class SmallCommitteeMemberBase(BaseModel):
    family_member_id: Optional[int] = None
    member_name: Optional[str] = None
    role: Optional[str] = None


class SmallCommitteeMemberCreate(SmallCommitteeMemberBase):
    pass


class SmallCommitteeMemberOut(SmallCommitteeMemberBase, TimestampMixin):
    id: int

    class Config:
        from_attributes = True


class SmallCommitteeDepartmentBase(BaseModel):
    name: str


class SmallCommitteeDepartmentCreate(SmallCommitteeDepartmentBase):
    members: List[SmallCommitteeMemberCreate] = []


class SmallCommitteeDepartmentOut(SmallCommitteeDepartmentBase, TimestampMixin):
    id: int
    members: List[SmallCommitteeMemberOut] = []

    class Config:
        from_attributes = True


class SmallCommitteeBase(BaseModel):
    name: str
    description: Optional[str] = None


class SmallCommitteeCreate(SmallCommitteeBase):
    departments: List[SmallCommitteeDepartmentCreate] = []


class SmallCommitteeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    departments: Optional[List[SmallCommitteeDepartmentCreate]] = None


class SmallCommitteeOut(SmallCommitteeBase, TimestampMixin):
    id: int
    departments: List[SmallCommitteeDepartmentOut] = []

    class Config:
        from_attributes = True
