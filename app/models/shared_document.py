from sqlalchemy import Column, Integer, String, DateTime, func, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class SharedDocument(Base):
    __tablename__ = "shared_documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)  # Store original filename
    file_path = Column(String, nullable=False)  # Store file path on disk
    size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)  # Optional description
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Track who uploaded
    uploaded_at = Column(DateTime, server_default=func.now())
    downloads = Column(Integer, default=0)
    is_public = Column(Boolean, default=True)  # Whether document is publicly accessible

    # Relationship with announcements (for flyers)
    announcement = relationship("Announcement", back_populates="flyer", uselist=False)

    # Relationship with user who uploaded
    uploader = relationship("User", foreign_keys=[uploaded_by])

    @property
    def is_flyer(self) -> bool:
        """Check if this document is used as an announcement flyer"""
        return self.announcement is not None