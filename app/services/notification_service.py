import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.chat import ChatRoom, Message, ChatRoomMember
from app.core.websocket_manager import connection_manager
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling push notifications and alerts"""
    
    def __init__(self):
        self.notification_queue = asyncio.Queue()
        self.notification_handlers = {}
        self.offline_notifications = {}  # Store notifications for offline users
    
    async def send_message_notification(self, message: Message, room: ChatRoom, sender: User):
        """Send notification for a new message"""
        try:
            db: Session = SessionLocal()
            
            # Get all room members except the sender
            members = db.query(ChatRoomMember).filter(
                ChatRoomMember.chat_room_id == room.id,
                ChatRoomMember.user_id != sender.id,
                ChatRoomMember.is_blocked == False
            ).all()
            
            for member in members:
                # Check if user is online
                if connection_manager.is_user_online(member.user_id):
                    # Send real-time notification via WebSocket
                    await self._send_realtime_notification(member.user_id, {
                        "type": "message_notification",
                        "title": f"New message from {sender.full_name}",
                        "body": self._get_message_preview(message),
                        "data": {
                            "message_id": message.id,
                            "room_id": room.id,
                            "room_name": room.name or f"Chat with {sender.full_name}",
                            "sender_id": sender.id,
                            "sender_name": sender.full_name,
                            "sender_avatar": sender.profile_pic,
                            "message_type": message.message_type.value,
                            "timestamp": message.created_at.isoformat()
                        }
                    })
                else:
                    # Store notification for offline user
                    await self._store_offline_notification(member.user_id, {
                        "type": "message",
                        "title": f"New message from {sender.full_name}",
                        "body": self._get_message_preview(message),
                        "data": {
                            "message_id": message.id,
                            "room_id": room.id,
                            "room_name": room.name or f"Chat with {sender.full_name}",
                            "sender_id": sender.id,
                            "sender_name": sender.full_name,
                            "timestamp": message.created_at.isoformat()
                        }
                    })
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error sending message notification: {e}")
    
    async def send_mention_notification(self, message: Message, mentioned_user_ids: List[int], sender: User):
        """Send notification for user mentions"""
        try:
            for user_id in mentioned_user_ids:
                if user_id == sender.id:  # Don't notify the sender
                    continue
                
                notification_data = {
                    "type": "mention_notification",
                    "title": f"{sender.full_name} mentioned you",
                    "body": self._get_message_preview(message),
                    "data": {
                        "message_id": message.id,
                        "room_id": message.chat_room_id,
                        "sender_id": sender.id,
                        "sender_name": sender.full_name,
                        "timestamp": message.created_at.isoformat()
                    }
                }
                
                if connection_manager.is_user_online(user_id):
                    await self._send_realtime_notification(user_id, notification_data)
                else:
                    await self._store_offline_notification(user_id, notification_data)
                    
        except Exception as e:
            logger.error(f"Error sending mention notification: {e}")
    
    async def send_reaction_notification(self, message: Message, reactor: User, emoji: str):
        """Send notification for message reactions"""
        try:
            # Only notify the message sender
            if message.sender_id == reactor.id:
                return  # Don't notify if user reacted to their own message
            
            notification_data = {
                "type": "reaction_notification",
                "title": f"{reactor.full_name} reacted to your message",
                "body": f"Reacted with {emoji}",
                "data": {
                    "message_id": message.id,
                    "room_id": message.chat_room_id,
                    "reactor_id": reactor.id,
                    "reactor_name": reactor.full_name,
                    "emoji": emoji,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            if connection_manager.is_user_online(message.sender_id):
                await self._send_realtime_notification(message.sender_id, notification_data)
            else:
                await self._store_offline_notification(message.sender_id, notification_data)
                
        except Exception as e:
            logger.error(f"Error sending reaction notification: {e}")
    
    async def send_room_invitation_notification(self, room: ChatRoom, inviter: User, invited_user_id: int):
        """Send notification for room invitations"""
        try:
            notification_data = {
                "type": "room_invitation",
                "title": f"{inviter.full_name} invited you to a chat",
                "body": f"Join '{room.name or 'Group Chat'}'",
                "data": {
                    "room_id": room.id,
                    "room_name": room.name,
                    "room_type": room.room_type.value,
                    "inviter_id": inviter.id,
                    "inviter_name": inviter.full_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            if connection_manager.is_user_online(invited_user_id):
                await self._send_realtime_notification(invited_user_id, notification_data)
            else:
                await self._store_offline_notification(invited_user_id, notification_data)
                
        except Exception as e:
            logger.error(f"Error sending room invitation notification: {e}")
    
    async def send_typing_notification(self, room_id: int, user: User, is_typing: bool):
        """Send typing indicator notification"""
        try:
            await connection_manager.broadcast_to_room(room_id, {
                "type": "typing_indicator",
                "data": {
                    "user_id": user.id,
                    "user_name": user.full_name,
                    "room_id": room_id,
                    "is_typing": is_typing,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, exclude_user=user.id)
            
        except Exception as e:
            logger.error(f"Error sending typing notification: {e}")
    
    async def send_presence_notification(self, user: User, is_online: bool):
        """Send user presence notification"""
        try:
            db: Session = SessionLocal()
            
            # Get all rooms where user is a member
            memberships = db.query(ChatRoomMember).filter(
                ChatRoomMember.user_id == user.id,
                ChatRoomMember.is_blocked == False
            ).all()
            
            for membership in memberships:
                await connection_manager.broadcast_to_room(membership.chat_room_id, {
                    "type": "presence_update",
                    "data": {
                        "user_id": user.id,
                        "user_name": user.full_name,
                        "is_online": is_online,
                        "last_seen": datetime.utcnow().isoformat(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }, exclude_user=user.id)
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error sending presence notification: {e}")
    
    async def send_system_notification(self, user_ids: List[int], title: str, body: str, data: Dict[str, Any] = None):
        """Send system notification to specific users"""
        try:
            notification_data = {
                "type": "system_notification",
                "title": title,
                "body": body,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for user_id in user_ids:
                if connection_manager.is_user_online(user_id):
                    await self._send_realtime_notification(user_id, notification_data)
                else:
                    await self._store_offline_notification(user_id, notification_data)
                    
        except Exception as e:
            logger.error(f"Error sending system notification: {e}")
    
    async def send_broadcast_notification(self, title: str, body: str, data: Dict[str, Any] = None):
        """Send broadcast notification to all online users"""
        try:
            notification_data = {
                "type": "broadcast_notification",
                "title": title,
                "body": body,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            online_users = connection_manager.get_online_users()
            for user_id in online_users:
                await self._send_realtime_notification(user_id, notification_data)
                
        except Exception as e:
            logger.error(f"Error sending broadcast notification: {e}")
    
    async def get_offline_notifications(self, user_id: int) -> List[Dict[str, Any]]:
        """Get stored notifications for a user when they come online"""
        try:
            notifications = self.offline_notifications.get(user_id, [])
            
            # Clear notifications after retrieving
            if user_id in self.offline_notifications:
                del self.offline_notifications[user_id]
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting offline notifications: {e}")
            return []
    
    async def send_offline_notifications(self, user_id: int):
        """Send stored offline notifications when user comes online"""
        try:
            notifications = await self.get_offline_notifications(user_id)
            
            for notification in notifications:
                await self._send_realtime_notification(user_id, notification)
                
        except Exception as e:
            logger.error(f"Error sending offline notifications: {e}")
    
    async def clear_notifications(self, user_id: int, notification_type: str = None):
        """Clear notifications for a user"""
        try:
            if user_id in self.offline_notifications:
                if notification_type:
                    # Clear specific type of notifications
                    self.offline_notifications[user_id] = [
                        notif for notif in self.offline_notifications[user_id]
                        if notif.get("type") != notification_type
                    ]
                else:
                    # Clear all notifications
                    del self.offline_notifications[user_id]
                    
        except Exception as e:
            logger.error(f"Error clearing notifications: {e}")
    
    async def get_notification_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user"""
        try:
            return len(self.offline_notifications.get(user_id, []))
        except Exception as e:
            logger.error(f"Error getting notification count: {e}")
            return 0
    
    async def _send_realtime_notification(self, user_id: int, notification_data: Dict[str, Any]):
        """Send real-time notification via WebSocket"""
        try:
            await connection_manager.send_personal_message(user_id, {
                "type": "notification",
                "data": notification_data
            })
            
        except Exception as e:
            logger.error(f"Error sending real-time notification: {e}")
    
    async def _store_offline_notification(self, user_id: int, notification_data: Dict[str, Any]):
        """Store notification for offline user"""
        try:
            if user_id not in self.offline_notifications:
                self.offline_notifications[user_id] = []
            
            # Add timestamp if not present
            if "timestamp" not in notification_data:
                notification_data["timestamp"] = datetime.utcnow().isoformat()
            
            self.offline_notifications[user_id].append(notification_data)
            
            # Limit stored notifications per user (keep last 100)
            if len(self.offline_notifications[user_id]) > 100:
                self.offline_notifications[user_id] = self.offline_notifications[user_id][-100:]
                
        except Exception as e:
            logger.error(f"Error storing offline notification: {e}")
    
    def _get_message_preview(self, message: Message) -> str:
        """Get a preview of the message content"""
        try:
            if message.message_type.value == "text":
                content = message.content or ""
                return content[:100] + "..." if len(content) > 100 else content
            elif message.message_type.value == "image":
                return "📷 Image"
            elif message.message_type.value == "audio":
                return "🎵 Audio message"
            elif message.message_type.value == "video":
                return "🎥 Video"
            elif message.message_type.value == "file":
                return f"📎 {message.file_name or 'File'}"
            elif message.message_type.value == "location":
                return "📍 Location"
            elif message.message_type.value == "contact":
                return "👤 Contact"
            elif message.message_type.value == "sticker":
                return "😊 Sticker"
            elif message.message_type.value == "gif":
                return "🎬 GIF"
            else:
                return "Message"
                
        except Exception as e:
            logger.error(f"Error getting message preview: {e}")
            return "Message"
    
    async def register_notification_handler(self, notification_type: str, handler):
        """Register a custom notification handler"""
        self.notification_handlers[notification_type] = handler
    
    async def unregister_notification_handler(self, notification_type: str):
        """Unregister a notification handler"""
        if notification_type in self.notification_handlers:
            del self.notification_handlers[notification_type]
    
    async def process_notification_queue(self):
        """Process queued notifications (background task)"""
        while True:
            try:
                # Get notification from queue
                notification = await self.notification_queue.get()
                
                # Process based on type
                notification_type = notification.get("type")
                if notification_type in self.notification_handlers:
                    handler = self.notification_handlers[notification_type]
                    await handler(notification)
                
                # Mark task as done
                self.notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing notification queue: {e}")
                await asyncio.sleep(1)
    
    async def queue_notification(self, notification: Dict[str, Any]):
        """Add notification to processing queue"""
        await self.notification_queue.put(notification)


# Global notification service instance
notification_service = NotificationService()