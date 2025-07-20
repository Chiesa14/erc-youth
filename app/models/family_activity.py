from sqlalchemy import Column, Integer, String, Date, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.schemas.family_activity import ActivityStatusEnum, ActivityCategoryEnum


class Activity(Base):
    __tablename__ = "family_activities"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(ActivityStatusEnum), nullable=False)
    category = Column(Enum(ActivityCategoryEnum), nullable=False)
    type = Column(String, nullable=False)  # We'll store type as string, but validate on input
    description = Column(Text, nullable=True)

