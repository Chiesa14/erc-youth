from datetime import datetime

from sqlalchemy import Column, Enum as SqlEnum, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.sql import func

from app.db.session import Base
from app.schemas.family_document import DocumentType

class FamilyDocument(Base):
    __tablename__ = "family_documents"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    file_path = Column(String, nullable=True)
    type = Column(SqlEnum(DocumentType), nullable=False)
    status = Column(String, nullable=False,default="pending")
    original_filename = Column(String, nullable=False)
    storage_type = Column(String, nullable=False, default="file")
    title = Column(String, nullable=True)
    content_json = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)

    # Timestamp fields (standardized)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Keep for backward compatibility
