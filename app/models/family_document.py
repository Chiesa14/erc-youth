from datetime import datetime

from sqlalchemy import Column, Enum as SqlEnum, String, DateTime, Integer, ForeignKey

from app.db.session import Base
from app.schemas.family_document import DocumentType

# Replace this import with the combined enum logic
class FamilyDocument(Base):
    __tablename__ = "family_documents"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    file_path = Column(String, nullable=False)
    type = Column(SqlEnum(DocumentType), nullable=False)
    status = Column(String, nullable=False,default="pending")
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    original_filename = Column(String, nullable=False)
