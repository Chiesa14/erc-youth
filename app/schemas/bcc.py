from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.utils.timestamps import TimestampMixin


class BccMemberProgressOut(BaseModel):
    member_id: int
    member_name: str
    family_id: int
    completed_classes: List[int]
    missing_classes: List[int]
    is_complete: bool
    completion_percent: float


class BccClassCompletionCreate(BaseModel):
    class_number: int


class BccClassCompletionOut(BaseModel, TimestampMixin):
    id: int
    member_id: int
    class_number: int
    completed_at: datetime
    recorded_by_user_id: Optional[int] = None

    class Config:
        from_attributes = True


class BccIncompleteMemberOut(BaseModel):
    member_id: int
    member_name: str
    phone: str
    email: Optional[str] = None
    family_id: int
    family_name: str
    family_category: str
    completed_classes: List[int]
    missing_classes: List[int]
    completion_percent: float


class BccFamilyCompletionOut(BaseModel):
    family_id: int
    is_complete: bool
    incomplete_members: List[BccMemberProgressOut]
