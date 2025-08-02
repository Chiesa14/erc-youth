import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, func
from app.db.session import SessionLocal
from app.models.chat import (
    ChatRoom, ChatRoomMember, Message, MessageReaction, MessageEditHistory,
    MessageReadReceipt, UserPresence, PinnedMessage, UserBlock, UserReport,
    ChatAnalytics, MessageTypeEnum, MessageStatusEnum, ChatRoomTypeEnum,
    UserRoleInChatEnum
)
from app.models.user import User
from app.schemas.chat import (
    ChatRoomCreate, ChatRoomUpdate, MessageCreate, MessageUpdate,
    MessageReactionCreate, UserPresenceUpdate, PinnedMessageCreate,
    UserBlockCreate, UserReportCreate, MessageSearchQuery
)
from app.core.websocket_manager import connection_manager
from app.services.encryption_service import EncryptionService
from app.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)


def make_aware(dt: Optional[datetime], tz=timezone.utc) -> Optional[datetime]:
    """Convert naive datetime to timezone-aware"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is in UTC timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ChatService:
    def __init__(self):
        self.encryption_service = EncryptionService()
        self.notification_service = NotificationService()

    # Chat Room Management
    async def create_chat_room(self, room_data: ChatRoomCreate, creator_id: int, db: Session = None) -> ChatRoom:
        """Create a new chat room"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            # Create the room
            room = ChatRoom(
                name=room_data.name,
                description=room_data.description,
                room_type=room_data.room_type,
                avatar_url=room_data.avatar_url,
                is_active=room_data.is_active,
                max_members=room_data.max_members,
                allow_media=room_data.allow_media,
                allow_voice=room_data.allow_voice,
                allow_file_sharing=room_data.allow_file_sharing,
                message_retention_days=room_data.message_retention_days,
                is_encrypted=room_data.is_encrypted
            )

            if room_data.is_encrypted:
                room.encryption_key = self.encryption_service.generate_room_key()

            db.add(room)
            db.flush()  # Get the room ID

            # Add creator as owner
            creator_membership = ChatRoomMember(
                user_id=creator_id,
                chat_room_id=room.id,
                role=UserRoleInChatEnum.owner,
                can_send_messages=True,
                can_send_media=True,
                can_add_members=True,
                can_remove_members=True,
                can_edit_room=True,
                can_pin_messages=True
            )
            db.add(creator_membership)

            # Add other members if specified
            for member_id in room_data.member_ids:
                if member_id != creator_id:
                    member = ChatRoomMember(
                        user_id=member_id,
                        chat_room_id=room.id,
                        role=UserRoleInChatEnum.member
                    )
                    db.add(member)

            db.commit()

            # Load all relationships before session might close
            room = db.query(ChatRoom).options(
                joinedload(ChatRoom.members).joinedload(ChatRoomMember.user),
                joinedload(ChatRoom.pinned_messages)
            ).filter(ChatRoom.id == room.id).first()

            # Force load all attributes
            _ = room.id
            _ = room.name
            _ = len(room.members)
            _ = len(room.pinned_messages)

            # Notify members about new room
            await self._notify_room_created(room.id, creator_id)

            return room

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating chat room: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    async def get_user_chat_rooms(self, user_id: int, page: int = 1, size: int = 20, db: Session = None) -> List[
        ChatRoom]:
        """Get chat rooms for a user with pagination"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            offset = (page - 1) * size

            rooms = db.query(ChatRoom).join(ChatRoomMember).filter(
                and_(
                    ChatRoomMember.user_id == user_id,
                    ChatRoomMember.is_blocked == False,
                    ChatRoom.is_active == True
                )
            ).options(
                joinedload(ChatRoom.members).joinedload(ChatRoomMember.user),
                joinedload(ChatRoom.pinned_messages)
            ).order_by(desc(ChatRoom.last_activity)).offset(offset).limit(size).all()

            # Force load all relationships and add unread count and last message for each room
            for room in rooms:
                # Force load attributes
                _ = room.id
                _ = room.name
                _ = len(room.members)
                _ = len(room.pinned_messages)

                room.unread_count = await self._get_unread_count(user_id, room.id, db)
                room.last_message = await self._get_last_message(room.id, db)

            return rooms

        except Exception as e:
            logger.error(f"Error getting user chat rooms: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    async def update_chat_room(self, room_id: int, room_data: ChatRoomUpdate, user_id: int,
                               db: Session = None) -> ChatRoom:
        """Update a chat room"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            # Check permissions
            if not await self._can_edit_room(user_id, room_id, db):
                raise PermissionError("User cannot edit this room")

            room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
            if not room:
                raise ValueError("Room not found")

            # Update fields
            for field, value in room_data.dict(exclude_unset=True).items():
                setattr(room, field, value)

            room.updated_at = utc_now()
            db.commit()

            # Load all relationships
            room = db.query(ChatRoom).options(
                joinedload(ChatRoom.members).joinedload(ChatRoomMember.user),
                joinedload(ChatRoom.pinned_messages)
            ).filter(ChatRoom.id == room_id).first()

            # Force load attributes
            _ = room.id
            _ = room.name
            _ = len(room.members)

            # Notify room members about update
            await connection_manager.broadcast_to_room(room_id, {
                "type": "room_updated",
                "data": {
                    "room_id": room_id,
                    "updated_by": user_id,
                    "timestamp": utc_now().isoformat()
                }
            })

            return room

        except Exception as e:
            if use_own_session:
                db.rollback()
            logger.error(f"Error updating chat room: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    # Message Management
    async def send_message(self, message_data: MessageCreate, sender_id: int, db: Session = None) -> Message:
        """Send a message to a chat room"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            # Check permissions
            if not await self._can_send_message(sender_id, message_data.chat_room_id, db):
                raise PermissionError("User cannot send messages in this room")

            # Check if user is blocked
            if await self._is_user_blocked_in_room(sender_id, message_data.chat_room_id, db):
                raise PermissionError("User is blocked in this room")

            # Ensure scheduled_at and auto_delete_at are timezone-aware
            scheduled_at = ensure_utc(message_data.scheduled_at)
            auto_delete_at = ensure_utc(message_data.auto_delete_at)

            # Validate reply_to_message_id - set to None if invalid
            reply_to_message_id = message_data.reply_to_message_id
            if reply_to_message_id is not None and reply_to_message_id <= 0:
                reply_to_message_id = None
            elif reply_to_message_id is not None:
                # Verify the message exists and is in the same room
                reply_message = db.query(Message).filter(
                    and_(
                        Message.id == reply_to_message_id,
                        Message.chat_room_id == message_data.chat_room_id,
                        Message.is_deleted == False
                    )
                ).first()
                if not reply_message:
                    reply_to_message_id = None

            # Create message
            message = Message(
                chat_room_id=message_data.chat_room_id,
                sender_id=sender_id,
                content=message_data.content,
                message_type=message_data.message_type,
                reply_to_message_id=reply_to_message_id,
                file_url=message_data.file_url,
                file_name=message_data.file_name,
                file_size=message_data.file_size,
                file_type=message_data.file_type,
                thumbnail_url=message_data.thumbnail_url,
                audio_duration=message_data.audio_duration,
                audio_waveform=message_data.audio_waveform,
                transcription=message_data.transcription,
                latitude=message_data.latitude,
                longitude=message_data.longitude,
                location_name=message_data.location_name,
                contact_data=message_data.contact_data,
                scheduled_at=scheduled_at,
                auto_delete_at=auto_delete_at,
                status=MessageStatusEnum.sent
            )

            # Handle encryption if room is encrypted
            room = db.query(ChatRoom).filter(ChatRoom.id == message_data.chat_room_id).first()
            if room and room.is_encrypted and message.content:
                message.encrypted_content = self.encryption_service.encrypt_message(
                    message.content, room.encryption_key
                )
                message.is_encrypted = True

            # Handle scheduled messages - compare timezone-aware datetimes
            current_time = utc_now()
            if scheduled_at and scheduled_at > current_time:
                message.is_scheduled = True
                message.status = MessageStatusEnum.sent  # Will be delivered later

            db.add(message)
            db.flush()

            # Update room last activity
            room.last_activity = current_time
            db.commit()

            # CRITICAL: Load all required relationships BEFORE session closes
            # This prevents DetachedInstanceError
            message = db.query(Message).options(
                joinedload(Message.sender),
                joinedload(Message.reactions).joinedload(MessageReaction.user),
                joinedload(Message.reply_to_message),
                joinedload(Message.edit_history),
                joinedload(Message.read_receipts).joinedload(MessageReadReceipt.user)
            ).filter(Message.id == message.id).first()

            # Make sure all attributes are loaded while session is active
            # This forces SQLAlchemy to load all data into memory
            _ = message.id
            _ = message.chat_room_id
            _ = message.sender_id
            _ = message.content
            _ = message.message_type
            _ = message.status
            _ = message.is_edited
            _ = message.is_deleted
            _ = message.is_pinned
            _ = message.is_scheduled
            _ = message.forward_count
            _ = message.created_at
            _ = message.updated_at
            _ = message.sender.full_name if message.sender else None
            _ = len(message.reactions)
            _ = len(message.edit_history)
            _ = len(message.read_receipts)

            # If not scheduled, broadcast immediately
            if not message.is_scheduled:
                await self._broadcast_message(message, db)
            else:
                # Schedule the message for later delivery
                await self._schedule_message_delivery(message)

            # Update analytics
            await self._update_message_analytics(message_data.chat_room_id, message_data.message_type, db)

            return message

        except Exception as e:
            if use_own_session:
                db.rollback()
            logger.error(f"Error sending message: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    async def get_messages(self, room_id: int, user_id: int, page: int = 1, size: int = 50, db: Session = None) -> List[
        Message]:
        """Get messages from a chat room with pagination"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            # Check room access
            if not await self._has_room_access(user_id, room_id, db):
                raise PermissionError("User does not have access to this room")

            offset = (page - 1) * size
            current_time = utc_now()

            messages = db.query(Message).filter(
                and_(
                    Message.chat_room_id == room_id,
                    Message.is_deleted == False,
                    or_(
                        Message.is_scheduled == False,
                        Message.scheduled_at <= current_time
                    )
                )
            ).options(
                joinedload(Message.sender),
                joinedload(Message.reactions).joinedload(MessageReaction.user),
                joinedload(Message.reply_to_message),
                joinedload(Message.edit_history),
                joinedload(Message.read_receipts).joinedload(MessageReadReceipt.user)
            ).order_by(desc(Message.created_at)).offset(offset).limit(size).all()

            # Force load all attributes for each message
            for message in messages:
                _ = message.id
                _ = message.content or ""
                _ = message.sender.full_name if message.sender else "Unknown"
                _ = len(message.reactions)
                _ = len(message.edit_history)
                _ = len(message.read_receipts)

            # Decrypt messages if needed
            room = db.query(ChatRoom).filter(ChatRoom.id == room_id).first()
            if room and room.is_encrypted:
                for message in messages:
                    if message.is_encrypted and message.encrypted_content:
                        message.content = self.encryption_service.decrypt_message(
                            message.encrypted_content, room.encryption_key
                        )

            # Mark messages as delivered/read
            await self._mark_messages_as_read(user_id, [m.id for m in messages], db)

            return list(reversed(messages))  # Return in chronological order

        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    async def edit_message(self, message_id: int, message_data: MessageUpdate, user_id: int,
                           db: Session = None) -> Message:
        """Edit a message"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if not message:
                raise ValueError("Message not found")

            # Check permissions
            if message.sender_id != user_id:
                raise PermissionError("User can only edit their own messages")

            # Check if message can be edited (e.g., within time limit)
            time_limit = timedelta(minutes=15)  # 15 minutes edit window
            current_time = utc_now()

            # Ensure message.created_at is timezone-aware for comparison
            message_created_at = ensure_utc(message.created_at)
            if current_time - message_created_at > time_limit:
                raise PermissionError("Message edit time limit exceeded")

            # Save edit history
            edit_history = MessageEditHistory(
                message_id=message_id,
                old_content=message.content or ""
            )
            db.add(edit_history)

            # Update message
            if message_data.content is not None:
                message.content = message_data.content

                # Re-encrypt if needed
                room = db.query(ChatRoom).filter(ChatRoom.id == message.chat_room_id).first()
                if room and room.is_encrypted:
                    message.encrypted_content = self.encryption_service.encrypt_message(
                        message.content, room.encryption_key
                    )

            message.is_edited = True
            message.updated_at = current_time

            db.commit()

            # Load all relationships
            message = db.query(Message).options(
                joinedload(Message.sender),
                joinedload(Message.reactions).joinedload(MessageReaction.user),
                joinedload(Message.reply_to_message),
                joinedload(Message.edit_history),
                joinedload(Message.read_receipts).joinedload(MessageReadReceipt.user)
            ).filter(Message.id == message_id).first()

            # Force load attributes
            _ = message.id
            _ = message.content
            _ = message.sender.full_name if message.sender else "Unknown"

            # Broadcast edit notification
            await connection_manager.broadcast_to_room(message.chat_room_id, {
                "type": "message_edited",
                "data": {
                    "message_id": message_id,
                    "new_content": message.content,
                    "edited_by": user_id,
                    "timestamp": current_time.isoformat()
                }
            })

            return message

        except Exception as e:
            if use_own_session:
                db.rollback()
            logger.error(f"Error editing message: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    async def delete_message(self, message_id: int, user_id: int, db: Session = None) -> bool:
        """Delete a message"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if not message:
                raise ValueError("Message not found")

            # Check permissions
            can_delete = (
                    message.sender_id == user_id or
                    await self._can_manage_room(user_id, message.chat_room_id, db)
            )

            if not can_delete:
                raise PermissionError("User cannot delete this message")

            # Soft delete
            message.is_deleted = True
            message.updated_at = utc_now()

            db.commit()

            # Broadcast deletion notification
            await connection_manager.broadcast_to_room(message.chat_room_id, {
                "type": "message_deleted",
                "data": {
                    "message_id": message_id,
                    "deleted_by": user_id,
                    "timestamp": utc_now().isoformat()
                }
            })

            return True

        except Exception as e:
            if use_own_session:
                db.rollback()
            logger.error(f"Error deleting message: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    # Reactions
    async def add_reaction(self, reaction_data: MessageReactionCreate, user_id: int, db: Session = None) -> Optional[
        MessageReaction]:
        """Add a reaction to a message"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            # Check if message exists and user has access
            message = db.query(Message).filter(Message.id == reaction_data.message_id).first()
            if not message:
                raise ValueError("Message not found")

            if not await self._has_room_access(user_id, message.chat_room_id, db):
                raise PermissionError("User does not have access to this room")

            # Check if reaction already exists
            existing_reaction = db.query(MessageReaction).filter(
                and_(
                    MessageReaction.message_id == reaction_data.message_id,
                    MessageReaction.user_id == user_id,
                    MessageReaction.emoji == reaction_data.emoji
                )
            ).first()

            if existing_reaction:
                # Remove existing reaction (toggle)
                db.delete(existing_reaction)
                db.commit()

                await connection_manager.broadcast_to_room(message.chat_room_id, {
                    "type": "reaction_removed",
                    "data": {
                        "message_id": reaction_data.message_id,
                        "user_id": user_id,
                        "emoji": reaction_data.emoji,
                        "timestamp": utc_now().isoformat()
                    }
                })

                return None

            # Add new reaction
            reaction = MessageReaction(
                message_id=reaction_data.message_id,
                user_id=user_id,
                emoji=reaction_data.emoji
            )

            db.add(reaction)
            db.commit()

            # Load reaction with user
            reaction = db.query(MessageReaction).options(
                joinedload(MessageReaction.user)
            ).filter(MessageReaction.id == reaction.id).first()

            # Force load attributes
            _ = reaction.id
            _ = reaction.user.full_name if reaction.user else "Unknown"

            # Broadcast reaction
            await connection_manager.broadcast_to_room(message.chat_room_id, {
                "type": "reaction_added",
                "data": {
                    "message_id": reaction_data.message_id,
                    "user_id": user_id,
                    "emoji": reaction_data.emoji,
                    "timestamp": utc_now().isoformat()
                }
            })

            return reaction

        except Exception as e:
            if use_own_session:
                db.rollback()
            logger.error(f"Error adding reaction: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    # Search
    async def search_messages(self, search_query: MessageSearchQuery, user_id: int, db: Session = None) -> List[
        Message]:
        """Search messages"""
        use_own_session = db is None
        if use_own_session:
            db = SessionLocal()

        try:
            query = db.query(Message).join(ChatRoom).join(ChatRoomMember).filter(
                and_(
                    ChatRoomMember.user_id == user_id,
                    ChatRoomMember.is_blocked == False,
                    Message.is_deleted == False
                )
            )

            # Apply filters
            if search_query.query:
                query = query.filter(Message.content.ilike(f"%{search_query.query}%"))

            if search_query.chat_room_id:
                query = query.filter(Message.chat_room_id == search_query.chat_room_id)

            if search_query.message_type:
                query = query.filter(Message.message_type == search_query.message_type)

            if search_query.sender_id:
                query = query.filter(Message.sender_id == search_query.sender_id)

            if search_query.date_from:
                date_from = ensure_utc(search_query.date_from)
                query = query.filter(Message.created_at >= date_from)

            if search_query.date_to:
                date_to = ensure_utc(search_query.date_to)
                query = query.filter(Message.created_at <= date_to)

            messages = query.options(
                joinedload(Message.sender),
                joinedload(Message.chat_room),
                joinedload(Message.reactions).joinedload(MessageReaction.user),
                joinedload(Message.reply_to_message),
                joinedload(Message.edit_history),
                joinedload(Message.read_receipts).joinedload(MessageReadReceipt.user)
            ).order_by(desc(Message.created_at)).limit(100).all()

            # Force load all attributes
            for message in messages:
                _ = message.id
                _ = message.content or ""
                _ = message.sender.full_name if message.sender else "Unknown"
                _ = len(message.reactions)

            return messages

        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            raise
        finally:
            if use_own_session:
                db.close()

    # Helper methods
    async def _can_send_message(self, user_id: int, room_id: int, db: Session) -> bool:
        """Check if user can send messages in a room"""
        membership = db.query(ChatRoomMember).filter(
            and_(
                ChatRoomMember.user_id == user_id,
                ChatRoomMember.chat_room_id == room_id,
                ChatRoomMember.is_blocked == False
            )
        ).first()

        return membership and membership.can_send_messages

    async def _has_room_access(self, user_id: int, room_id: int, db: Session) -> bool:
        """Check if user has access to a room"""
        membership = db.query(ChatRoomMember).filter(
            and_(
                ChatRoomMember.user_id == user_id,
                ChatRoomMember.chat_room_id == room_id,
                ChatRoomMember.is_blocked == False
            )
        ).first()

        return membership is not None

    async def _can_edit_room(self, user_id: int, room_id: int, db: Session) -> bool:
        """Check if user can edit a room"""
        membership = db.query(ChatRoomMember).filter(
            and_(
                ChatRoomMember.user_id == user_id,
                ChatRoomMember.chat_room_id == room_id
            )
        ).first()

        return membership and membership.can_edit_room

    async def _can_manage_room(self, user_id: int, room_id: int, db: Session) -> bool:
        """Check if user can manage a room"""
        membership = db.query(ChatRoomMember).filter(
            and_(
                ChatRoomMember.user_id == user_id,
                ChatRoomMember.chat_room_id == room_id
            )
        ).first()

        return membership and membership.role.value in ["admin", "owner", "moderator"]

    async def _is_user_blocked_in_room(self, user_id: int, room_id: int, db: Session) -> bool:
        """Check if user is blocked in a room"""
        membership = db.query(ChatRoomMember).filter(
            and_(
                ChatRoomMember.user_id == user_id,
                ChatRoomMember.chat_room_id == room_id
            )
        ).first()

        return membership and membership.is_blocked

    async def _get_unread_count(self, user_id: int, room_id: int, db: Session) -> int:
        """Get unread message count for a user in a room"""
        membership = db.query(ChatRoomMember).filter(
            and_(
                ChatRoomMember.user_id == user_id,
                ChatRoomMember.chat_room_id == room_id
            )
        ).first()

        if not membership:
            return 0

        last_read_id = membership.last_read_message_id or 0

        unread_count = db.query(Message).filter(
            and_(
                Message.chat_room_id == room_id,
                Message.id > last_read_id,
                Message.is_deleted == False,
                Message.sender_id != user_id
            )
        ).count()

        return unread_count

    async def _get_last_message(self, room_id: int, db: Session) -> Optional[Message]:
        """Get the last message in a room"""
        message = db.query(Message).filter(
            and_(
                Message.chat_room_id == room_id,
                Message.is_deleted == False
            )
        ).options(
            joinedload(Message.sender)
        ).order_by(desc(Message.created_at)).first()

        if message:
            # Force load attributes
            _ = message.id
            _ = message.content or ""
            _ = message.sender.full_name if message.sender else "Unknown"

        return message

    async def _mark_messages_as_read(self, user_id: int, message_ids: List[int], db: Session):
        """Mark messages as read for a user"""
        if not message_ids:
            return

        # Update read receipts
        for message_id in message_ids:
            existing_receipt = db.query(MessageReadReceipt).filter(
                and_(
                    MessageReadReceipt.message_id == message_id,
                    MessageReadReceipt.user_id == user_id
                )
            ).first()

            if not existing_receipt:
                receipt = MessageReadReceipt(
                    message_id=message_id,
                    user_id=user_id
                )
                db.add(receipt)

        # Update last read message for user
        last_message_id = max(message_ids)
        message = db.query(Message).filter(Message.id == last_message_id).first()
        if message:
            membership = db.query(ChatRoomMember).filter(
                and_(
                    ChatRoomMember.user_id == user_id,
                    ChatRoomMember.chat_room_id == message.chat_room_id
                )
            ).first()

            if membership:
                membership.last_read_message_id = last_message_id
                membership.last_seen = utc_now()

        db.commit()

    async def _broadcast_message(self, message: Message, db: Session):
        """Broadcast a message to room members"""
        # Get sender info
        sender = db.query(User).filter(User.id == message.sender_id).first()

        await connection_manager.broadcast_to_room(message.chat_room_id, {
            "type": "new_message",
            "data": {
                "message_id": message.id,
                "chat_room_id": message.chat_room_id,
                "sender_id": message.sender_id,
                "sender_name": sender.full_name if sender else "Unknown",
                "content": message.content,
                "message_type": message.message_type.value,
                "created_at": message.created_at.isoformat(),
                "reply_to_message_id": message.reply_to_message_id,
                "file_url": message.file_url,
                "thumbnail_url": message.thumbnail_url
            }
        })

    async def _schedule_message_delivery(self, message: Message):
        """Schedule a message for later delivery"""
        # This would typically use a task queue like Celery
        # For now, we'll use asyncio
        current_time = utc_now()
        scheduled_time = ensure_utc(message.scheduled_at)

        if scheduled_time and scheduled_time > current_time:
            delay = (scheduled_time - current_time).total_seconds()
            asyncio.create_task(self._deliver_scheduled_message(message.id, delay))

    async def _deliver_scheduled_message(self, message_id: int, delay: float):
        """Deliver a scheduled message after delay"""
        await asyncio.sleep(delay)

        db: Session = SessionLocal()
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message and message.is_scheduled:
                message.is_scheduled = False
                message.status = MessageStatusEnum.delivered
                db.commit()

                await self._broadcast_message(message, db)
        except Exception as e:
            logger.error(f"Error delivering scheduled message {message_id}: {e}")
        finally:
            db.close()

    async def _update_message_analytics(self, room_id: int, message_type: MessageTypeEnum, db: Session):
        """Update message analytics"""
        today = utc_now().date()

        analytics = db.query(ChatAnalytics).filter(
            and_(
                ChatAnalytics.chat_room_id == room_id,
                func.date(ChatAnalytics.date) == today
            )
        ).first()

        if not analytics:
            analytics = ChatAnalytics(
                chat_room_id=room_id,
                date=utc_now(),
                # Initialize all counters to 0 to prevent None += int errors
                total_messages=0,
                text_messages=0,
                media_messages=0,
                file_messages=0,
                active_users=0,
                new_members=0,
                total_reactions=0,
                total_replies=0
            )
            db.add(analytics)

        # Ensure all fields have default values if they're None
        analytics.total_messages = (analytics.total_messages or 0) + 1

        if message_type == MessageTypeEnum.text:
            analytics.text_messages = (analytics.text_messages or 0) + 1
        elif message_type in [MessageTypeEnum.image, MessageTypeEnum.video, MessageTypeEnum.audio]:
            analytics.media_messages = (analytics.media_messages or 0) + 1
        elif message_type == MessageTypeEnum.file:
            analytics.file_messages = (analytics.file_messages or 0) + 1

        db.commit()

    async def _notify_room_created(self, room_id: int, creator_id: int):
        """Notify members about new room creation"""
        await connection_manager.broadcast_to_room(room_id, {
            "type": "room_created",
            "data": {
                "room_id": room_id,
                "created_by": creator_id,
                "timestamp": utc_now().isoformat()
            }
        })


# Global chat service instance
chat_service = ChatService()