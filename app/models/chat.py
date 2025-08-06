from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.db.session import Base


class MessageTypeEnum(PyEnum):
    text = "text"
    image = "image"
    audio = "audio"
    video = "video"
    file = "file"
    location = "location"
    contact = "contact"
    sticker = "sticker"
    gif = "gif"


class MessageStatusEnum(PyEnum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class ChatRoomTypeEnum(PyEnum):
    direct = "direct"
    group = "group"
    channel = "channel"


class UserRoleInChatEnum(PyEnum):
    member = "member"
    admin = "admin"
    owner = "owner"
    moderator = "moderator"


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)  # For group chats
    description = Column(Text, nullable=True)
    room_type = Column(Enum(ChatRoomTypeEnum), default=ChatRoomTypeEnum.direct)
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    max_members = Column(Integer, default=100)

    # Settings
    allow_media = Column(Boolean, default=True)
    allow_voice = Column(Boolean, default=True)
    allow_file_sharing = Column(Boolean, default=True)
    message_retention_days = Column(Integer, default=0)  # 0 means forever

    # Encryption
    encryption_key = Column(String, nullable=True)
    is_encrypted = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    messages = relationship("Message", back_populates="chat_room", cascade="all, delete-orphan")
    members = relationship("ChatRoomMember", back_populates="chat_room", cascade="all, delete-orphan")
    pinned_messages = relationship("PinnedMessage", back_populates="chat_room", cascade="all, delete-orphan")


class ChatRoomMember(Base):
    __tablename__ = "chat_room_members"

    id = Column(Integer, primary_key=True, index=True)
    # Updated with CASCADE
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(UserRoleInChatEnum), default=UserRoleInChatEnum.member)

    # Permissions
    can_send_messages = Column(Boolean, default=True)
    can_send_media = Column(Boolean, default=True)
    can_add_members = Column(Boolean, default=False)
    can_remove_members = Column(Boolean, default=False)
    can_edit_room = Column(Boolean, default=False)
    can_pin_messages = Column(Boolean, default=False)

    # Status
    is_muted = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    muted_until = Column(DateTime(timezone=True), nullable=True)

    # Activity
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_read_message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", overlaps="chat_memberships")
    chat_room = relationship("ChatRoom", back_populates="members")
    last_read_message = relationship("Message", foreign_keys=[last_read_message_id])


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    # Updated with CASCADE
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Message content
    content = Column(Text, nullable=True)
    message_type = Column(Enum(MessageTypeEnum), default=MessageTypeEnum.text)

    # Reply functionality - SET NULL when referenced message is deleted
    reply_to_message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)

    # Forward functionality - SET NULL when referenced message is deleted
    forwarded_from_message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    forward_count = Column(Integer, default=0)

    # Media and files
    file_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)

    # Audio specific
    audio_duration = Column(Float, nullable=True)
    audio_waveform = Column(JSON, nullable=True)
    transcription = Column(Text, nullable=True)

    # Location specific
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String, nullable=True)

    # Contact specific
    contact_data = Column(JSON, nullable=True)

    # Message status and delivery
    status = Column(Enum(MessageStatusEnum), default=MessageStatusEnum.sent)
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    is_scheduled = Column(Boolean, default=False)

    # Auto-delete
    auto_delete_at = Column(DateTime(timezone=True), nullable=True)

    # Encryption
    encrypted_content = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    chat_room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], overlaps="sent_messages")
    reply_to_message = relationship("Message", remote_side=[id], foreign_keys=[reply_to_message_id])
    forwarded_from_message = relationship("Message", remote_side=[id], foreign_keys=[forwarded_from_message_id])
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")
    edit_history = relationship("MessageEditHistory", back_populates="message", cascade="all, delete-orphan")
    read_receipts = relationship("MessageReadReceipt", back_populates="message", cascade="all, delete-orphan")


class MessageReaction(Base):
    __tablename__ = "message_reactions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    # Updated with CASCADE
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    emoji = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="reactions")
    user = relationship("User", overlaps="message_reactions")

class MessageEditHistory(Base):
    __tablename__ = "message_edit_history"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    old_content = Column(Text, nullable=False)
    edited_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="edit_history")


class MessageReadReceipt(Base):
    __tablename__ = "message_read_receipts"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    # Updated with CASCADE
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="read_receipts")
    user = relationship("User", overlaps="message_read_receipts")


class UserPresence(Base):
    __tablename__ = "user_presence"

    id = Column(Integer, primary_key=True, index=True)
    # Updated with CASCADE
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    status_message = Column(String, nullable=True)
    is_typing_in_room = Column(Integer, ForeignKey("chat_rooms.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", overlaps="user_presence")
    typing_in_room = relationship("ChatRoom")


class PinnedMessage(Base):
    __tablename__ = "pinned_messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    # Updated with CASCADE
    pinned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pinned_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chat_room = relationship("ChatRoom", back_populates="pinned_messages")
    message = relationship("Message")
    pinned_by = relationship("User", overlaps="pinned_messages")


class UserBlock(Base):
    __tablename__ = "user_blocks"

    id = Column(Integer, primary_key=True, index=True)
    # Updated with CASCADE
    blocker_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    blocked_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    blocked_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String, nullable=True)

    # Relationships
    blocker = relationship("User", foreign_keys=[blocker_id], overlaps="blocked_users")
    blocked = relationship("User", foreign_keys=[blocked_id], overlaps="blocking_users")


class UserReport(Base):
    __tablename__ = "user_reports"

    id = Column(Integer, primary_key=True, index=True)
    # Updated with CASCADE
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reported_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    reason = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, reviewed, resolved
    reported_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], overlaps="reported_users")
    reported = relationship("User", foreign_keys=[reported_id], overlaps="reports_against")
    message = relationship("Message")


class ChatAnalytics(Base):
    __tablename__ = "chat_analytics"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)

    total_messages = Column(Integer, default=0, nullable=False)
    text_messages = Column(Integer, default=0, nullable=False)
    media_messages = Column(Integer, default=0, nullable=False)
    file_messages = Column(Integer, default=0, nullable=False)
    active_users = Column(Integer, default=0, nullable=False)
    new_members = Column(Integer, default=0, nullable=False)
    total_reactions = Column(Integer, default=0, nullable=False)
    total_replies = Column(Integer, default=0, nullable=False)

    # Relationships
    chat_room = relationship("ChatRoom")