from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class BccClassCompletion(Base):
    __tablename__ = "bcc_class_completions"
    __table_args__ = (
        UniqueConstraint("member_id", "class_number", name="uq_bcc_member_class"),
        CheckConstraint("class_number >= 1 AND class_number <= 7", name="ck_bcc_class_number_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True)
    class_number = Column(Integer, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    member = relationship("FamilyMember", back_populates="bcc_class_completions")
