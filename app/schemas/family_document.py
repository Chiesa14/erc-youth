from enum import Enum
from pydantic import BaseModel, field_serializer
from datetime import datetime


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

class DocumentOut(BaseModel):
    id: int
    family_id: int
    type: DocumentType
    original_filename: str
    status: str
    uploaded_at: datetime

    @field_serializer('uploaded_at')
    def serialize_uploaded_at(self, uploaded_at: datetime, _info):
        return uploaded_at.isoformat()
      # Accept both report and letter status strings

    class Config:
        from_attributes = True
