from datetime import datetime

from sqlalchemy import Column, Enum as SqlEnum, String, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func

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
    original_filename = Column(String, nullable=False)

    # Timestamp fields (standardized)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Keep for backward compatibility
