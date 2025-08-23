from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.schemas.feedback import FeedbackStatusEnum, FeedbackCategoryEnum

class Reply(Base):
    __tablename__ = "replies"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedback.id"), nullable=False)
    author = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    date = Column(Date, nullable=False, default=func.current_date())

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    feedback = relationship("Feedback", back_populates="replies")

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    author = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    date = Column(Date, nullable=False, default=func.current_date())
    status = Column(Enum(FeedbackStatusEnum), nullable=False, default=FeedbackStatusEnum.new)
    category = Column(Enum(FeedbackCategoryEnum), nullable=False)
    parent_notified = Column(Boolean, nullable=False, default=False)

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    family = relationship("Family", back_populates="feedback")
    replies = relationship("Reply", back_populates="feedback", cascade="all, delete-orphan")