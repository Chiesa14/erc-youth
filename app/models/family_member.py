from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Date, Enum, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.schemas.family_member import GraduationModeEnum,AccessPermissionEnum, EducationLevelEnum
from app.schemas.user import GenderEnum


class FamilyMemberInvitation(Base):
    __tablename__ = "family_member_invitations"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("family_members.id", ondelete="CASCADE"))
    temp_password = Column(String, nullable=False)
    is_activated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)

    member = relationship("FamilyMember", back_populates="invitation")

class FamilyMemberPermission(Base):
    __tablename__ = "family_member_permissions"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("family_members.id", ondelete="CASCADE"))
    permission = Column(Enum(AccessPermissionEnum), nullable=False)

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    member = relationship("FamilyMember", back_populates="permissions")


class FamilyMember(Base):
    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_member_phone"),
        UniqueConstraint("email", name="uq_member_email"),
        UniqueConstraint("name", "family_id", name="uq_family_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    phone = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=True, unique=True)  # Optional but must be unique if present

    home_address = Column(String)
    date_of_birth = Column(Date)
    gender = Column(Enum(GenderEnum))
    education_level = Column(Enum(EducationLevelEnum))
    employment_status = Column(String)
    bcc_class_participation = Column(Boolean)
    year_of_graduation = Column(Integer)
    graduation_mode = Column(Enum(GraduationModeEnum),nullable=True)
    parental_status = Column(Boolean)

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    family = relationship("Family", back_populates="members")
    permissions = relationship("FamilyMemberPermission", cascade="all, delete", back_populates="member")
    invitation = relationship("FamilyMemberInvitation", back_populates="member", uselist=False, cascade="all, delete")

