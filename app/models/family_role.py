from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.sql import func

from app.db.session import Base
from app.schemas.user import RoleEnum


class FamilyRole(Base):
    __tablename__ = "family_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    system_role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.other)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
