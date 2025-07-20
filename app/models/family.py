from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.session import Base

class Family(Base):
    __tablename__ = "families"
    __table_args__ = (UniqueConstraint('category', 'name', name='uq_family_category_name'),)

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    name = Column(String, nullable=False)

    users = relationship("User", back_populates="family")
    members = relationship("FamilyMember", back_populates="family")  # <-- ADD THIS
