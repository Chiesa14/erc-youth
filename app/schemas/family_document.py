from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class DocumentType(str, Enum):
    report = "report"
    letter = "letter"

class DocumentUpload(BaseModel):
    type: DocumentType

class DocumentOut(BaseModel):
    id: int
    family_id: int
    type: DocumentType
    uploaded_at: datetime
    original_filename: str

    class Config:
        from_attributes = True
