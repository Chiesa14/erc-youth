from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, Text, DateTime, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.schemas.family_activity import ActivityStatusEnum, ActivityCategoryEnum


class Activity(Base):
    __tablename__ = "family_activities"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    status = Column(Enum(ActivityStatusEnum), nullable=False)
    category = Column(Enum(ActivityCategoryEnum), nullable=False)
    type = Column(String, nullable=False)  # We'll store type as string, but validate on input
    description = Column(Text, nullable=True)

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    family = relationship("Family", back_populates="activities")

    # QR check-in relationships
    checkin_session = relationship(
        "ActivityCheckinSession",
        back_populates="activity",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    attendances = relationship(
        "ActivityAttendance",
        back_populates="activity",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

