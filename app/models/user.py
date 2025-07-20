from pydantic import EmailStr
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.schemas.user import GenderEnum,FamilyCategoryEnum,RoleEnum




class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    gender = Column(Enum(GenderEnum), nullable=False)
    phone = Column(String, nullable=False)
    family_category = Column(Enum(FamilyCategoryEnum), nullable=True)
    family_name = Column(String, nullable=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.other)
    other = Column(String, nullable=True)
    profile_pic = Column(String, nullable=True)

    access_code = Column(String(4), unique=True, index=True, nullable=True)

    biography = Column(String, nullable=True)  # optional biography field

    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    family = relationship("Family", back_populates="users")


