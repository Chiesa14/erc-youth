import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import logging
from app.schemas.chat import WebSocketMessage, TypingIndicator, OnlineStatus
from app.models.chat import UserPresence
from app.db.session import SessionLocal
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Store active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
        # Store room memberships: {room_id: {user_id}}
        self.room_members: Dict[int, Set[int]] = {}
        # Store typing indicators: {room_id: {user_id: timestamp}}
        self.typing_indicators: Dict[int, Dict[int, datetime]] = {}
        # Store user presence: {user_id: last_activity}
        self.user_presence: Dict[int, datetime] = {}
        # Connection metadata: {connection_id: {user_id, room_ids}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, connection_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Initialize user connections if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        # Store the connection
        self.active_connections[user_id][connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "room_ids": set(),
            "connected_at": datetime.utcnow()
        }
        
        # Update user presence
        await self.update_user_presence(user_id, True)
        
        logger.info(f"User {user_id} connected with connection {connection_id}")

    async def disconnect(self, user_id: int, connection_id: str):
        """Remove a WebSocket connection"""
        try:
            # Remove from active connections
            if user_id in self.active_connections:
                if connection_id in self.active_connections[user_id]:
                    del self.active_connections[user_id][connection_id]
                
                # If no more connections for this user, clean up
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    await self.update_user_presence(user_id, False)
            
            # Clean up room memberships for this connection
            if connection_id in self.connection_metadata:
                room_ids = self.connection_metadata[connection_id].get("room_ids", set())
                for room_id in room_ids:
                    await self.leave_room(user_id, room_id, connection_id)
                
                del self.connection_metadata[connection_id]
            
            logger.info(f"User {user_id} disconnected connection {connection_id}")
            
        except Exception as e:
            logger.error(f"Error during disconnect for user {user_id}: {e}")

    async def join_room(self, user_id: int, room_id: int, connection_id: str):
        """Add user to a chat room"""
        # Initialize room if not exists
        if room_id not in self.room_members:
            self.room_members[room_id] = set()
        
        # Add user to room
        self.room_members[room_id].add(user_id)
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["room_ids"].add(room_id)
        
        # Notify other room members that user joined
        await self.broadcast_to_room(room_id, {
            "type": "user_joined_room",
            "data": {
                "user_id": user_id,
                "room_id": room_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_user=user_id)
        
        logger.info(f"User {user_id} joined room {room_id}")

    async def leave_room(self, user_id: int, room_id: int, connection_id: str):
        """Remove user from a chat room"""
        # Remove user from room
        if room_id in self.room_members:
            self.room_members[room_id].discard(user_id)
            
            # Clean up empty rooms
            if not self.room_members[room_id]:
                del self.room_members[room_id]
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["room_ids"].discard(room_id)
        
        # Clear typing indicator if user was typing
        if room_id in self.typing_indicators:
            self.typing_indicators[room_id].pop(user_id, None)
        
        # Notify other room members that user left
        await self.broadcast_to_room(room_id, {
            "type": "user_left_room",
            "data": {
                "user_id": user_id,
                "room_id": room_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_user=user_id)
        
        logger.info(f"User {user_id} left room {room_id}")

    async def send_personal_message(self, user_id: int, message: Dict[str, Any]):
        """Send message to a specific user across all their connections"""
        if user_id in self.active_connections:
            disconnected_connections = []
            
            for connection_id, websocket in self.active_connections[user_id].items():
                try:
                    await websocket.send_text(json.dumps(message, default=str))
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}, connection {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
            
            # Clean up disconnected connections
            for connection_id in disconnected_connections:
                await self.disconnect(user_id, connection_id)

    async def broadcast_to_room(self, room_id: int, message: Dict[str, Any], exclude_user: Optional[int] = None):
        """Broadcast message to all users in a room"""
        if room_id not in self.room_members:
            return
        
        for user_id in self.room_members[room_id]:
            if exclude_user and user_id == exclude_user:
                continue
            
            await self.send_personal_message(user_id, message)

    async def handle_typing_indicator(self, user_id: int, room_id: int, is_typing: bool):
        """Handle typing indicator updates"""
        if room_id not in self.typing_indicators:
            self.typing_indicators[room_id] = {}
        
        if is_typing:
            self.typing_indicators[room_id][user_id] = datetime.utcnow()
        else:
            self.typing_indicators[room_id].pop(user_id, None)
        
        # Broadcast typing indicator to room members
        await self.broadcast_to_room(room_id, {
            "type": "typing_indicator",
            "data": {
                "user_id": user_id,
                "room_id": room_id,
                "is_typing": is_typing,
                "timestamp": datetime.utcnow().isoformat()
            }
        }, exclude_user=user_id)

    async def update_user_presence(self, user_id: int, is_online: bool):
        """Update user online/offline status"""
        db: Session = SessionLocal()
        try:
            # Update in database
            presence = db.query(UserPresence).filter(UserPresence.user_id == user_id).first()
            if presence:
                presence.is_online = is_online
                presence.last_seen = datetime.utcnow()
                presence.updated_at = datetime.utcnow()
            else:
                presence = UserPresence(
                    user_id=user_id,
                    is_online=is_online,
                    last_seen=datetime.utcnow()
                )
                db.add(presence)
            
            db.commit()
            
            # Update in memory
            if is_online:
                self.user_presence[user_id] = datetime.utcnow()
            else:
                self.user_presence.pop(user_id, None)
            
            # Broadcast presence update to all rooms where user is a member
            for room_id, members in self.room_members.items():
                if user_id in members:
                    await self.broadcast_to_room(room_id, {
                        "type": "presence_update",
                        "data": {
                            "user_id": user_id,
                            "is_online": is_online,
                            "last_seen": datetime.utcnow().isoformat()
                        }
                    }, exclude_user=user_id)
                    
        except Exception as e:
            logger.error(f"Error updating user presence for user {user_id}: {e}")
            db.rollback()
        finally:
            db.close()

    async def cleanup_typing_indicators(self):
        """Clean up old typing indicators (run periodically)"""
        current_time = datetime.utcnow()
        timeout_seconds = 10  # Consider typing stopped after 10 seconds
        
        for room_id in list(self.typing_indicators.keys()):
            for user_id in list(self.typing_indicators[room_id].keys()):
                last_typing = self.typing_indicators[room_id][user_id]
                if (current_time - last_typing).total_seconds() > timeout_seconds:
                    # Remove typing indicator and notify room
                    del self.typing_indicators[room_id][user_id]
                    await self.broadcast_to_room(room_id, {
                        "type": "typing_indicator",
                        "data": {
                            "user_id": user_id,
                            "room_id": room_id,
                            "is_typing": False,
                            "timestamp": current_time.isoformat()
                        }
                    }, exclude_user=user_id)
            
            # Clean up empty room typing indicators
            if not self.typing_indicators[room_id]:
                del self.typing_indicators[room_id]

    def get_room_members(self, room_id: int) -> Set[int]:
        """Get all members currently connected to a room"""
        return self.room_members.get(room_id, set())

    def get_online_users(self) -> Set[int]:
        """Get all currently online users"""
        return set(self.active_connections.keys())

    def is_user_online(self, user_id: int) -> bool:
        """Check if a user is currently online"""
        return user_id in self.active_connections

    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, {}))

    async def handle_message(self, websocket: WebSocket, user_id: int, connection_id: str, message_data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        try:
            message_type = message_data.get("type")
            data = message_data.get("data", {})
            
            if message_type == "join_room":
                room_id = data.get("room_id")
                if room_id:
                    await self.join_room(user_id, room_id, connection_id)
            
            elif message_type == "leave_room":
                room_id = data.get("room_id")
                if room_id:
                    await self.leave_room(user_id, room_id, connection_id)
            
            elif message_type == "typing":
                room_id = data.get("room_id")
                is_typing = data.get("is_typing", False)
                if room_id is not None:
                    await self.handle_typing_indicator(user_id, room_id, is_typing)
            
            elif message_type == "ping":
                # Respond with pong to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }))
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from user {user_id}: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "data": {"message": "Failed to process message"}
            }))


# Global connection manager instance
connection_manager = ConnectionManager()


async def start_cleanup_task():
    """Start background task to clean up typing indicators"""
    while True:
        try:
            await connection_manager.cleanup_typing_indicators()
            await asyncio.sleep(5)  # Run every 5 seconds
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(5)