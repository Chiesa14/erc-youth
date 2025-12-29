from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ActivityCheckinSession(Base):
    __tablename__ = "family_activity_checkin_sessions"
    __table_args__ = (UniqueConstraint('activity_id', name='uq_activity_checkin_session_activity_id'),)

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("family_activities.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    activity = relationship("Activity", back_populates="checkin_session")


class ActivityAttendance(Base):
    __tablename__ = "family_activity_attendances"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("family_activities.id", ondelete="CASCADE"), nullable=False, index=True)
    attendee_name = Column(String, nullable=False)
    family_of_origin_id = Column(Integer, ForeignKey("families.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    activity = relationship("Activity", back_populates="attendances")
    family_of_origin = relationship("Family")
