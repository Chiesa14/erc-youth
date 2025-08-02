from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status, UploadFile, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ChatRoom, ChatRoomCreate, ChatRoomUpdate, ChatRoomPagination,
    Message, MessageCreate, MessageUpdate, MessagePagination,
    MessageReaction, MessageReactionCreate,
    UserPresence, UserPresenceUpdate,
    PinnedMessage, PinnedMessageCreate,
    UserBlock, UserBlockCreate,
    UserReport, UserReportCreate,
    MessageSearchQuery, MessageSearchResult,
    ChatAnalytics
)
from app.services.chat_service import chat_service
from app.services.file_upload import file_upload_service
from app.core.websocket_manager import connection_manager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ChatController:
    """Controller for handling chat-related business logic and request processing"""

    def __init__(self):
        self.chat_service = chat_service
        self.file_upload_service = file_upload_service
        self.connection_manager = connection_manager

    # Chat Room Management Methods
    async def create_chat_room(self, room_data: ChatRoomCreate, current_user: User, db: Session = None) -> ChatRoom:
        """Create a new chat room"""
        try:
            room = await self.chat_service.create_chat_room(room_data, current_user.id, db)
            return room
        except Exception as e:
            logger.error(f"Error creating chat room: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create chat room"
            )

    async def get_user_chat_rooms(self, page: int, size: int, current_user: User, db: Session = None) -> List[ChatRoom]:
        """Get user's chat rooms with pagination"""
        try:
            rooms = await self.chat_service.get_user_chat_rooms(current_user.id, page, size, db)
            return rooms
        except Exception as e:
            logger.error(f"Error getting user chat rooms: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get chat rooms"
            )

    async def get_chat_room(self, room_id: int, current_user: User, db: Session) -> ChatRoom:
        """Get a specific chat room"""
        try:
            # Check access permissions
            if not await self.chat_service._has_room_access(current_user.id, room_id, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this room"
                )

            from app.models.chat import ChatRoom as ChatRoomModel
            from sqlalchemy.orm import joinedload

            room = db.query(ChatRoomModel).options(
                joinedload(ChatRoomModel.members).joinedload(ChatRoomModel.members.property.mapper.class_.user),
                joinedload(ChatRoomModel.pinned_messages)
            ).filter(ChatRoomModel.id == room_id).first()

            if not room:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Room not found"
                )

            return room
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting chat room: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get chat room"
            )

    async def update_chat_room(self, room_id: int, room_data: ChatRoomUpdate, current_user: User,
                               db: Session = None) -> ChatRoom:
        """Update a chat room"""
        try:
            room = await self.chat_service.update_chat_room(room_id, room_data, current_user.id, db)
            return room
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to edit this room"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error updating chat room: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update chat room"
            )

    async def delete_chat_room(self, room_id: int, current_user: User, db: Session) -> Dict[str, str]:
        """Delete a chat room (soft delete)"""
        try:
            # Check permissions
            if not await self.chat_service._can_manage_room(current_user.id, room_id, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied to delete this room"
                )

            from app.models.chat import ChatRoom as ChatRoomModel
            room = db.query(ChatRoomModel).filter(ChatRoomModel.id == room_id).first()
            if not room:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Room not found"
                )

            room.is_active = False
            db.commit()

            # Notify room members
            await self.connection_manager.broadcast_to_room(room_id, {
                "type": "room_deleted",
                "data": {
                    "room_id": room_id,
                    "deleted_by": current_user.id,
                    "timestamp": room.updated_at.isoformat()
                }
            })

            return {"message": "Room deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting chat room: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete chat room"
            )

    # Message Management Methods
    async def send_message(self, room_id: int, message_data: MessageCreate, current_user: User,
                           db: Session = None) -> Message:
        """Send a message to a chat room"""
        try:
            # Ensure room_id matches
            message_data.chat_room_id = room_id

            message = await self.chat_service.send_message(message_data, current_user.id, db)
            return message
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send message"
            )

    async def get_messages(self, room_id: int, page: int, size: int, current_user: User, db: Session = None) -> List[
        Message]:
        """Get messages from a chat room"""
        try:
            messages = await self.chat_service.get_messages(room_id, current_user.id, page, size, db)
            return messages
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this room"
            )
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get messages"
            )

    async def edit_message(self, message_id: int, message_data: MessageUpdate, current_user: User,
                           db: Session = None) -> Message:
        """Edit a message"""
        try:
            message = await self.chat_service.edit_message(message_id, message_data, current_user.id, db)
            return message
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to edit message"
            )

    async def delete_message(self, message_id: int, current_user: User, db: Session = None) -> Dict[str, str]:
        """Delete a message"""
        try:
            success = await self.chat_service.delete_message(message_id, current_user.id, db)
            if success:
                return {"message": "Message deleted successfully"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete message"
                )
        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete message"
            )

    # File Upload Methods
    async def upload_image(self, file: UploadFile, current_user: User) -> Dict[str, Any]:
        """Upload an image for messages"""
        try:
            if not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be an image"
                )

            result = await self.file_upload_service.upload_image(file, current_user.id)
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image"
            )

    async def upload_file(self, file: UploadFile, current_user: User) -> Dict[str, Any]:
        """Upload a file for messages"""
        try:
            result = await self.file_upload_service.upload_file(file, current_user.id)
            return result
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file"
            )

    async def upload_audio(self, file: UploadFile, current_user: User) -> Dict[str, Any]:
        """Upload an audio file for messages"""
        try:
            if not file.content_type.startswith('audio/'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be an audio file"
                )

            result = await self.file_upload_service.upload_audio(file, current_user.id)
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading audio: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload audio"
            )

    # Reaction Methods
    async def add_reaction(self, message_id: int, reaction_data: MessageReactionCreate, current_user: User,
                           db: Session = None) -> Optional[MessageReaction]:
        """Add or remove a reaction to a message"""
        try:
            # Ensure message_id matches
            reaction_data.message_id = message_id

            reaction = await self.chat_service.add_reaction(reaction_data, current_user.id, db)
            return reaction
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this room"
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error adding reaction: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add reaction"
            )

    # Search Methods
    async def search_messages(self, search_query: MessageSearchQuery, current_user: User, db: Session = None) -> List[
        Message]:
        """Search messages"""
        try:
            messages = await self.chat_service.search_messages(search_query, current_user.id, db)
            return messages
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to search messages"
            )

    # User Presence Methods
    async def get_user_presence(self, user_id: int, current_user: User, db: Session) -> UserPresence:
        """Get user presence status"""
        try:
            from app.models.chat import UserPresence as UserPresenceModel

            presence = db.query(UserPresenceModel).filter(
                UserPresenceModel.user_id == user_id
            ).first()

            if not presence:
                # Create default presence
                presence = UserPresenceModel(
                    user_id=user_id,
                    is_online=self.connection_manager.is_user_online(user_id)
                )
                db.add(presence)
                db.commit()
                db.refresh(presence)
            else:
                # Update online status from connection manager
                presence.is_online = self.connection_manager.is_user_online(user_id)

            return presence
        except Exception as e:
            logger.error(f"Error getting user presence: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user presence"
            )

    async def update_user_presence(self, presence_data: UserPresenceUpdate, current_user: User,
                                   db: Session) -> UserPresence:
        """Update user presence status"""
        try:
            from app.models.chat import UserPresence as UserPresenceModel

            presence = db.query(UserPresenceModel).filter(
                UserPresenceModel.user_id == current_user.id
            ).first()

            if not presence:
                presence = UserPresenceModel(user_id=current_user.id)
                db.add(presence)

            # Update fields
            for field, value in presence_data.dict(exclude_unset=True).items():
                setattr(presence, field, value)

            db.commit()
            db.refresh(presence)

            return presence
        except Exception as e:
            logger.error(f"Error updating user presence: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user presence"
            )

    # Room Member Management Methods
    async def add_room_member(self, room_id: int, user_id: int, current_user: User, db: Session) -> Dict[str, str]:
        """Add a member to a chat room"""
        try:
            # Check permissions
            if not await self.chat_service._can_manage_room(current_user.id, room_id, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied to add members"
                )

            from app.models.chat import ChatRoomMember, ChatRoom as ChatRoomModel

            # Check if room exists
            room = db.query(ChatRoomModel).filter(ChatRoomModel.id == room_id).first()
            if not room:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Room not found"
                )

            # Check if user is already a member
            existing_member = db.query(ChatRoomMember).filter(
                ChatRoomMember.chat_room_id == room_id,
                ChatRoomMember.user_id == user_id
            ).first()

            if existing_member:
                if existing_member.is_blocked:
                    existing_member.is_blocked = False
                    db.commit()
                    return {"message": "User unblocked and added to room"}
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User is already a member"
                    )

            # Add new member
            new_member = ChatRoomMember(
                chat_room_id=room_id,
                user_id=user_id
            )
            db.add(new_member)
            db.commit()

            # Notify room members
            await self.connection_manager.broadcast_to_room(room_id, {
                "type": "member_added",
                "data": {
                    "room_id": room_id,
                    "user_id": user_id,
                    "added_by": current_user.id,
                    "timestamp": new_member.joined_at.isoformat()
                }
            })

            return {"message": "Member added successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding room member: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add member"
            )

    async def remove_room_member(self, room_id: int, user_id: int, current_user: User, db: Session) -> Dict[str, str]:
        """Remove a member from a chat room"""
        try:
            # Check permissions
            if not await self.chat_service._can_manage_room(current_user.id, room_id, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied to remove members"
                )

            from app.models.chat import ChatRoomMember

            member = db.query(ChatRoomMember).filter(
                ChatRoomMember.chat_room_id == room_id,
                ChatRoomMember.user_id == user_id
            ).first()

            if not member:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Member not found"
                )

            # Block the member instead of deleting
            member.is_blocked = True
            db.commit()

            # Notify room members
            await self.connection_manager.broadcast_to_room(room_id, {
                "type": "member_removed",
                "data": {
                    "room_id": room_id,
                    "user_id": user_id,
                    "removed_by": current_user.id,
                    "timestamp": member.updated_at.isoformat()
                }
            })

            return {"message": "Member removed successfully"}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error removing room member: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove member"
            )

    # Analytics Methods
    async def get_room_analytics(self, room_id: int, days: int, current_user: User, db: Session) -> List[ChatAnalytics]:
        """Get chat room analytics"""
        try:
            # Check permissions
            if not await self.chat_service._can_manage_room(current_user.id, room_id, db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied to view analytics"
                )

            from app.models.chat import ChatAnalytics as ChatAnalyticsModel
            from datetime import datetime, timedelta

            start_date = datetime.utcnow() - timedelta(days=days)

            analytics = db.query(ChatAnalyticsModel).filter(
                ChatAnalyticsModel.chat_room_id == room_id,
                ChatAnalyticsModel.date >= start_date
            ).order_by(ChatAnalyticsModel.date.desc()).all()

            return analytics

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting room analytics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get analytics"
            )


# Global chat controller instance
chat_controller = ChatController()