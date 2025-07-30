from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum

from app.schemas.announcement import AnnouncementType


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    type = Column(Enum(AnnouncementType), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    flyer_id = Column(Integer, ForeignKey("shared_documents.id"), nullable=True)

    user = relationship("User", back_populates="announcements")
    flyer = relationship("SharedDocument", back_populates="announcement")
    views = relationship("AnnouncementView", back_populates="announcement")

    @property
    def view_count(self):
        return func.count(self.views).scalar() or 0

class AnnouncementView(Base):
    __tablename__ = "announcement_views"

    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(Integer, ForeignKey("announcements.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(String, nullable=True)
    viewed_at = Column(DateTime, server_default=func.now())

    announcement = relationship("Announcement", back_populates="views")
    user = relationship("User")