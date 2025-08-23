from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
from enum import Enum
from app.utils.timestamps import TimestampMixin

class PriorityEnum(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class CommentTypeEnum(str, Enum):
    general = "general"
    feedback = "feedback"
    suggestion = "suggestion"
    endorsement = "endorsement"
    concern = "concern"

class ProgramStatusEnum(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class ProgramCreate(BaseModel):
    family_id: int
    program_name: str
    description: str
    requested_budget: str
    participants: int
    priority: PriorityEnum

class ProgramUpdate(BaseModel):
    status: ProgramStatusEnum

class ProgramResponse(BaseModel, TimestampMixin):
    id: int
    family_id: int
    family_name: str
    program_name: str
    description: str
    submitted_date: date
    requested_budget: str
    participants: int
    priority: PriorityEnum
    status: ProgramStatusEnum

    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    family_id: int
    comment: str
    comment_type: CommentTypeEnum

class CommentResponse(BaseModel, TimestampMixin):
    id: int
    family_id: int
    family_name: str
    comment: str
    date: date
    comment_type: CommentTypeEnum
    status: str

    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    """
    Unified response model for both programs and comments
    Always includes family information and category
    """
    id: int
    type: str  # "program" or "comment"
    family_id: int
    family_name: str
    family_category: str
    title: str
    description: str
    date: date
    status: str
    priority: Optional[str] = None  # Only for programs
    requested_budget: Optional[str] = None  # Only for programs
    participants: Optional[int] = None  # Only for programs
    comment_type: Optional[str] = None  # Only for comments

    class Config:
        from_attributes = True

class RecommendationFilters(BaseModel):
    """
    Filter model for recommendation queries
    """
    family_ids: Optional[List[int]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    program_status: Optional[List[ProgramStatusEnum]] = None
    comment_types: Optional[List[CommentTypeEnum]] = None
    priority: Optional[List[PriorityEnum]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None

class RecommendationSummaryResponse(BaseModel):
    """
    Summary statistics for recommendations
    """
    total_recommendations: int
    programs: dict
    comments: dict