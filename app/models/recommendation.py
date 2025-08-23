from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.schemas.recommendation import PriorityEnum, CommentTypeEnum, ProgramStatusEnum

class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    program_name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    submitted_date = Column(Date, nullable=False, default=func.current_date())
    requested_budget = Column(String, nullable=False)
    participants = Column(Integer, nullable=False)
    priority = Column(Enum(PriorityEnum), nullable=False)
    status = Column(Enum(ProgramStatusEnum), nullable=False, default=ProgramStatusEnum.pending)

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    family = relationship("Family", back_populates="programs")

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    comment = Column(Text, nullable=False)
    date = Column(Date, nullable=False, default=func.current_date())
    comment_type = Column(Enum(CommentTypeEnum), nullable=False)
    status = Column(String, nullable=False, default="active")

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    family = relationship("Family", back_populates="comments")