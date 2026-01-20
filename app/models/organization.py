from enum import Enum

from sqlalchemy import Column, Integer, String, Enum as SQLEnum, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class OrgLevelEnum(str, Enum):
    vision = "vision"
    executive = "executive"
    leader = "leader"
    committee = "committee"


class OrganizationPosition(Base):
    __tablename__ = "organization_positions"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(SQLEnum(OrgLevelEnum), nullable=False)
    name = Column(String, nullable=False)
    id_name = Column(String, nullable=True)
    role = Column(String, nullable=False)
    position = Column(String, nullable=False)
    photo = Column(String, nullable=True)
    sort_order = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SmallCommittee(Base):
    __tablename__ = "small_committees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    departments = relationship(
        "SmallCommitteeDepartment",
        back_populates="committee",
        cascade="all, delete-orphan",
    )


class SmallCommitteeDepartment(Base):
    __tablename__ = "small_committee_departments"

    id = Column(Integer, primary_key=True, index=True)
    committee_id = Column(Integer, ForeignKey("small_committees.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    committee = relationship("SmallCommittee", back_populates="departments")
    members = relationship(
        "SmallCommitteeMember",
        back_populates="department",
        cascade="all, delete-orphan",
    )


class SmallCommitteeMember(Base):
    __tablename__ = "small_committee_members"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("small_committee_departments.id", ondelete="CASCADE"), nullable=False)

    family_member_id = Column(Integer, ForeignKey("family_members.id"), nullable=True)
    member_name = Column(String, nullable=True)
    role = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    department = relationship("SmallCommitteeDepartment", back_populates="members")
