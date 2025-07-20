from datetime import datetime
from sqlalchemy import Integer, Column, ForeignKey, DateTime, String, Enum
from app.schemas.family_document import DocumentType

from app.db.session import Base


class FamilyDocument(Base):
    __tablename__ = "family_documents"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    file_path = Column(String, nullable=False)  # e.g. uploads/documents/1/3_report.pdf
    type = Column(Enum(DocumentType), nullable=False)  # letter or report
    uploaded_at = Column(DateTime, default=datetime.now())
    original_filename = Column(String, nullable=False)
