from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
from enum import Enum
from app.utils.timestamps import TimestampMixin

class FeedbackStatusEnum(str, Enum):
    new = "new"
    pending = "pending"
    resolved = "resolved"

class FeedbackCategoryEnum(str, Enum):
    praise = "praise"
    suggestion = "suggestion"
    question = "question"
    concern = "concern"

class ReplyCreate(BaseModel):
    content: str


class ReplyResponse(BaseModel):
    id: int
    author: str
    content: str
    date: date

    class Config:
        from_attributes = True

class FeedbackCreate(BaseModel):
    family_id: int
    author: str
    subject: str
    content: str
    category: FeedbackCategoryEnum
    rating: Optional[int] = None

class FeedbackUpdate(BaseModel):
    status: Optional[FeedbackStatusEnum] = None
    parent_notified: Optional[bool] = None

class FeedbackResponse(BaseModel, TimestampMixin):
    id: int
    family_id: int
    family_name: str
    author: str
    subject: str
    content: str
    rating: Optional[int]
    date: date
    status: FeedbackStatusEnum
    category: FeedbackCategoryEnum
    parent_notified: bool
    replies: List[ReplyResponse]

    class Config:
        from_attributes = True