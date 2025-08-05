from enum import Enum
from pydantic import BaseModel, field_serializer
from datetime import datetime
from app.utils.timestamps import TimestampMixin


class DocumentType(str, Enum):
    report = "report"
    letter = "letter"

class ReportStatus(str, Enum):
    submitted = "submitted"
    pending = "pending"

class LetterStatus(str, Enum):
    pending = "pending"
    reviewed = "reviewed"
    approved = "approved"

class DocumentOut(BaseModel, TimestampMixin):
    id: int
    family_id: int
    type: DocumentType
    original_filename: str
    status: str
    uploaded_at: datetime

    @field_serializer('uploaded_at')
    def serialize_uploaded_at(self, uploaded_at: datetime, _info):
        return uploaded_at.isoformat()

    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime, _info):
        return created_at.isoformat()

    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: datetime, _info):
        return updated_at.isoformat()

    class Config:
        from_attributes = True
