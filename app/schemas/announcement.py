from pydantic import BaseModel, computed_field
from datetime import datetime
from enum import Enum
from typing import Optional

class AnnouncementType(str, Enum):
    important = "important"
    announcement = "announcement"
    event = "event"

class AnnouncementBase(BaseModel):
    title: str
    content: str
    type: AnnouncementType

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    type: Optional[AnnouncementType] = None

class AnnouncementOut(AnnouncementBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    flyer_id: Optional[int] = None

    _view_count: int = 0  # Private field for storage, initialize with default

    @computed_field
    @property
    def view_count(self) -> int:
        return self._view_count  # Return the internal value

    class Config:
        from_attributes = True