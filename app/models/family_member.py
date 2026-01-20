from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, Date, Enum, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.schemas.family_member import GraduationModeEnum, AccessPermissionEnum, EducationLevelEnum, ParentGuardianStatusEnum, EmploymentTypeEnum
from app.schemas.user import GenderEnum
from app.models.bcc_class_completion import BccClassCompletion


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
    id_name = Column(String, nullable=True)  # ID Name from docs
    deliverance_name = Column(String, nullable=True)  # Deliverance/Spiritual name

    phone = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=True, unique=True)  # Optional but must be unique if present
    profile_photo = Column(String, nullable=True)  # Path to uploaded profile photo

    # Residence details (district/sector/cell/village)
    home_address = Column(String)
    district = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    cell = Column(String, nullable=True)
    village = Column(String, nullable=True)
    living_arrangement = Column(String, nullable=True)  # e.g., "with family", "alone"

    date_of_birth = Column(Date)
    gender = Column(Enum(GenderEnum))
    
    # BCC Classes
    education_level = Column(Enum(EducationLevelEnum))
    bcc_class_participation = Column(Boolean)
    bcc_class_status = Column(String, nullable=True)  # "Graduate", "Ongoing", "Not yet Started"
    year_of_graduation = Column(Integer)
    graduation_mode = Column(Enum(GraduationModeEnum), nullable=True)
    
    # Commission and Parent/Guardian
    commission = Column(String, nullable=True)  # Church commission assignment
    parent_guardian_status = Column(Enum(ParentGuardianStatusEnum), nullable=True)
    parental_status = Column(Boolean)  # Keep for backwards compatibility

    # Occupation - detailed fields per docs
    employment_status = Column(String)
    employment_type = Column(Enum(EmploymentTypeEnum), nullable=True)
    job_title = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    business_name = Column(String, nullable=True)
    work_type = Column(String, nullable=True)  # For freelance
    work_description = Column(String, nullable=True)
    work_location = Column(String, nullable=True)
    
    # Student fields
    institution = Column(String, nullable=True)
    program = Column(String, nullable=True)
    student_level = Column(String, nullable=True)

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    family_id = Column(Integer, ForeignKey("families.id"), nullable=False)
    family = relationship("Family", back_populates="members")
    permissions = relationship("FamilyMemberPermission", cascade="all, delete", back_populates="member")
    invitation = relationship("FamilyMemberInvitation", back_populates="member", uselist=False, cascade="all, delete")
    bcc_class_completions = relationship(
        "BccClassCompletion",
        back_populates="member",
        cascade="all, delete",
    )
