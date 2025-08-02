from sqlalchemy import Column, Integer, String, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Family(Base):
    __tablename__ = "families"
    __table_args__ = (UniqueConstraint('category', 'name', name='uq_family_category_name'),)

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    name = Column(String, nullable=False)

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    users = relationship("User", back_populates="family")
    members = relationship("FamilyMember", back_populates="family")  # <-- ADD THIS
    prayer_chains = relationship("PrayerChain", back_populates="family")