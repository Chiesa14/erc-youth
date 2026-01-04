from pydantic import EmailStr
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.schemas.user import GenderEnum, FamilyCategoryEnum, RoleEnum


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    deliverance_name = Column(String, nullable=True)
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

    # Timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Foreign key relationships
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    family_role_id = Column(Integer, ForeignKey("family_roles.id"), nullable=True)

    # Relationships with CASCADE DELETE
    family = relationship("Family", back_populates="users")
    family_role = relationship("FamilyRole")
    announcements = relationship("Announcement", back_populates="user", cascade="all, delete-orphan")

    # Chat-related relationships with cascade delete
    sent_messages = relationship("Message",
                                 foreign_keys="Message.sender_id",
                                 cascade="all, delete-orphan",
                                 passive_deletes=True)

    chat_memberships = relationship("ChatRoomMember",
                                    foreign_keys="ChatRoomMember.user_id",
                                    cascade="all, delete-orphan",
                                    passive_deletes=True)

    message_reactions = relationship("MessageReaction",
                                     foreign_keys="MessageReaction.user_id",
                                     cascade="all, delete-orphan",
                                     passive_deletes=True)

    message_read_receipts = relationship("MessageReadReceipt",
                                         foreign_keys="MessageReadReceipt.user_id",
                                         cascade="all, delete-orphan",
                                         passive_deletes=True)

    user_presence = relationship("UserPresence",
                                 foreign_keys="UserPresence.user_id",
                                 cascade="all, delete-orphan",
                                 passive_deletes=True,
                                 uselist=False)  # One-to-one relationship

    pinned_messages = relationship("PinnedMessage",
                                   foreign_keys="PinnedMessage.pinned_by_user_id",
                                   cascade="all, delete-orphan",
                                   passive_deletes=True)

    # User blocking relationships
    blocked_users = relationship("UserBlock",
                                 foreign_keys="UserBlock.blocker_id",
                                 cascade="all, delete-orphan",
                                 passive_deletes=True,
                                 overlaps="blocker")

    blocking_users = relationship("UserBlock",
                                  foreign_keys="UserBlock.blocked_id",
                                  cascade="all, delete-orphan",
                                  passive_deletes=True,
                                  overlaps="blocked")

    # User reporting relationships
    reported_users = relationship("UserReport",
                                  foreign_keys="UserReport.reporter_id",
                                  cascade="all, delete-orphan",
                                  passive_deletes=True,
                                  overlaps="reporter")

    reports_against = relationship("UserReport",
                                   foreign_keys="UserReport.reported_id",
                                   cascade="all, delete-orphan",
                                   passive_deletes=True,
                                   overlaps="reported")