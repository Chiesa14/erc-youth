from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageTypeEnum(str, Enum):
    text = "text"
    image = "image"
    audio = "audio"
    video = "video"
    file = "file"
    location = "location"
    contact = "contact"
    sticker = "sticker"
    gif = "gif"


class MessageStatusEnum(str, Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"


class ChatRoomTypeEnum(str, Enum):
    direct = "direct"
    group = "group"
    channel = "channel"


class UserRoleInChatEnum(str, Enum):
    member = "member"
    admin = "admin"
    owner = "owner"
    moderator = "moderator"


# Base schemas
class ChatRoomBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    room_type: ChatRoomTypeEnum = ChatRoomTypeEnum.direct
    avatar_url: Optional[str] = None
    is_active: bool = True
    max_members: int = 100
    allow_media: bool = True
    allow_voice: bool = True
    allow_file_sharing: bool = True
    message_retention_days: int = 0
    is_encrypted: bool = False


class ChatRoomCreate(ChatRoomBase):
    member_ids: Optional[List[int]] = []


class ChatRoomUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    max_members: Optional[int] = None
    allow_media: Optional[bool] = None
    allow_voice: Optional[bool] = None
    allow_file_sharing: Optional[bool] = None
    message_retention_days: Optional[int] = None


class ChatRoomMemberBase(BaseModel):
    user_id: int
    role: UserRoleInChatEnum = UserRoleInChatEnum.member
    can_send_messages: bool = True
    can_send_media: bool = True
    can_add_members: bool = False
    can_remove_members: bool = False
    can_edit_room: bool = False
    can_pin_messages: bool = False
    is_muted: bool = False
    muted_until: Optional[datetime] = None


class ChatRoomMemberCreate(ChatRoomMemberBase):
    chat_room_id: int


class ChatRoomMemberUpdate(BaseModel):
    role: Optional[UserRoleInChatEnum] = None
    can_send_messages: Optional[bool] = None
    can_send_media: Optional[bool] = None
    can_add_members: Optional[bool] = None
    can_remove_members: Optional[bool] = None
    can_edit_room: Optional[bool] = None
    can_pin_messages: Optional[bool] = None
    is_muted: Optional[bool] = None
    muted_until: Optional[datetime] = None


class MessageBase(BaseModel):
    content: Optional[str] = None
    message_type: MessageTypeEnum = MessageTypeEnum.text
    reply_to_message_id: Optional[int] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    thumbnail_url: Optional[str] = None
    audio_duration: Optional[float] = None
    audio_waveform: Optional[Dict[str, Any]] = None
    transcription: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    contact_data: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    auto_delete_at: Optional[datetime] = None

    @validator('reply_to_message_id')
    def validate_reply_to_message_id(cls, v):
        """Convert 0 or negative values to None for foreign key compatibility"""
        if v is not None and v <= 0:
            return None
        return v

    @validator('file_size')
    def validate_file_size(cls, v):
        """Convert 0 to None for optional file size"""
        if v is not None and v <= 0:
            return None
        return v

    @validator('audio_duration')
    def validate_audio_duration(cls, v):
        """Convert 0 to None for optional audio duration"""
        if v is not None and v <= 0:
            return None
        return v

    @validator('latitude')
    def validate_latitude(cls, v):
        """Validate latitude range and convert 0 to None"""
        if v is not None:
            if v == 0:
                return None
            if not -90 <= v <= 90:
                raise ValueError('Latitude must be between -90 and 90 degrees')
        return v

    @validator('longitude')
    def validate_longitude(cls, v):
        """Validate longitude range and convert 0 to None"""
        if v is not None:
            if v == 0:
                return None
            if not -180 <= v <= 180:
                raise ValueError('Longitude must be between -180 and 180 degrees')
        return v

    @validator('content')
    def validate_content(cls, v, values):
        """Ensure content is provided for text messages"""
        message_type = values.get('message_type', MessageTypeEnum.text)
        if message_type == MessageTypeEnum.text and (not v or v.strip() == ''):
            raise ValueError('Content is required for text messages')
        return v


class MessageCreate(MessageBase):
    chat_room_id: int

    @validator('chat_room_id')
    def validate_chat_room_id(cls, v):
        """Ensure chat_room_id is positive"""
        if v <= 0:
            raise ValueError('chat_room_id must be a positive integer')
        return v


class MessageUpdate(BaseModel):
    content: Optional[str] = None

    @validator('content')
    def validate_content(cls, v):
        """Ensure content is not empty when provided"""
        if v is not None and v.strip() == '':
            raise ValueError('Content cannot be empty')
        return v


class MessageReactionBase(BaseModel):
    emoji: str

    @validator('emoji')
    def validate_emoji(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Emoji cannot be empty')
        return v


class MessageReactionCreate(MessageReactionBase):
    message_id: int

    @validator('message_id')
    def validate_message_id(cls, v):
        """Ensure message_id is positive"""
        if v <= 0:
            raise ValueError('message_id must be a positive integer')
        return v


class UserPresenceBase(BaseModel):
    is_online: bool = False
    status_message: Optional[str] = None
    is_typing_in_room: Optional[int] = None

    @validator('is_typing_in_room')
    def validate_is_typing_in_room(cls, v):
        """Convert 0 or negative values to None"""
        if v is not None and v <= 0:
            return None
        return v


class UserPresenceUpdate(UserPresenceBase):
    pass


class PinnedMessageCreate(BaseModel):
    message_id: int
    chat_room_id: int

    @validator('message_id')
    def validate_message_id(cls, v):
        if v <= 0:
            raise ValueError('message_id must be a positive integer')
        return v

    @validator('chat_room_id')
    def validate_chat_room_id(cls, v):
        if v <= 0:
            raise ValueError('chat_room_id must be a positive integer')
        return v


class UserBlockCreate(BaseModel):
    blocked_id: int
    reason: Optional[str] = None

    @validator('blocked_id')
    def validate_blocked_id(cls, v):
        if v <= 0:
            raise ValueError('blocked_id must be a positive integer')
        return v


class UserReportCreate(BaseModel):
    reported_id: int
    message_id: Optional[int] = None
    reason: str
    description: Optional[str] = None

    @validator('reported_id')
    def validate_reported_id(cls, v):
        if v <= 0:
            raise ValueError('reported_id must be a positive integer')
        return v

    @validator('message_id')
    def validate_message_id(cls, v):
        if v is not None and v <= 0:
            return None
        return v


# Response schemas
class UserSimple(BaseModel):
    id: int
    full_name: str
    email: str
    profile_pic: Optional[str] = None

    class Config:
        from_attributes = True


class MessageReaction(MessageReactionBase):
    id: int
    user_id: int
    user: UserSimple
    created_at: datetime

    class Config:
        from_attributes = True


class MessageEditHistory(BaseModel):
    id: int
    old_content: str
    edited_at: datetime

    class Config:
        from_attributes = True


class MessageReadReceipt(BaseModel):
    id: int
    user_id: int
    user: UserSimple
    read_at: datetime

    class Config:
        from_attributes = True


class Message(MessageBase):
    id: int
    chat_room_id: int
    sender_id: int
    sender: UserSimple
    status: MessageStatusEnum
    is_edited: bool
    is_deleted: bool
    is_pinned: bool
    is_scheduled: bool
    forward_count: int
    created_at: datetime
    updated_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    reactions: List[MessageReaction] = []
    edit_history: List[MessageEditHistory] = []
    read_receipts: List[MessageReadReceipt] = []
    reply_to_message: Optional['Message'] = None

    class Config:
        from_attributes = True


class ChatRoomMember(ChatRoomMemberBase):
    id: int
    chat_room_id: int
    user: UserSimple
    is_blocked: bool
    joined_at: datetime
    last_seen: datetime
    last_read_message_id: Optional[int] = None

    class Config:
        from_attributes = True


class PinnedMessage(BaseModel):
    id: int
    message_id: int
    message: Message
    pinned_by_user_id: int
    pinned_by: UserSimple
    pinned_at: datetime

    class Config:
        from_attributes = True


class ChatRoom(ChatRoomBase):
    id: int
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    members: List[ChatRoomMember] = []
    pinned_messages: List[PinnedMessage] = []
    unread_count: Optional[int] = 0
    last_message: Optional[Message] = None

    class Config:
        from_attributes = True


class UserPresence(UserPresenceBase):
    id: int
    user_id: int
    last_seen: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBlock(BaseModel):
    id: int
    blocker_id: int
    blocked_id: int
    blocked: UserSimple
    blocked_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class UserReport(BaseModel):
    id: int
    reporter_id: int
    reported_id: int
    reported: UserSimple
    message_id: Optional[int] = None
    reason: str
    description: Optional[str] = None
    status: str
    reported_at: datetime

    class Config:
        from_attributes = True


class ChatAnalytics(BaseModel):
    id: int
    chat_room_id: int
    date: datetime
    total_messages: int
    text_messages: int
    media_messages: int
    file_messages: int
    active_users: int
    new_members: int
    total_reactions: int
    total_replies: int

    class Config:
        from_attributes = True


# WebSocket message schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    room_id: Optional[int] = None
    user_id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TypingIndicator(BaseModel):
    user_id: int
    chat_room_id: int
    is_typing: bool
    user: UserSimple


class OnlineStatus(BaseModel):
    user_id: int
    is_online: bool
    last_seen: datetime
    user: UserSimple


# Pagination schemas
class MessagePagination(BaseModel):
    messages: List[Message]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class ChatRoomPagination(BaseModel):
    chat_rooms: List[ChatRoom]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


# Search schemas
class MessageSearchQuery(BaseModel):
    query: str
    chat_room_id: Optional[int] = None
    message_type: Optional[MessageTypeEnum] = None
    sender_id: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    @validator('chat_room_id')
    def validate_chat_room_id(cls, v):
        if v is not None and v <= 0:
            return None
        return v

    @validator('sender_id')
    def validate_sender_id(cls, v):
        if v is not None and v <= 0:
            return None
        return v


class MessageSearchResult(BaseModel):
    messages: List[Message]
    total: int
    query: str


# Update forward references
Message.model_rebuild()