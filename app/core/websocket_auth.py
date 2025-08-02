import jwt
from typing import Optional
from fastapi import WebSocket, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
from app.models.user import User
from app.db.session import SessionLocal
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.JWTError as e:
        logger.warning(f"JWT Error: {e}")
        return None


def get_user_from_token(token: str) -> Optional[User]:
    """Get user from JWT token"""
    payload = verify_token(token)
    if not payload:
        return None
    
    user_email = payload.get("sub")
    print(user_email)
    if not user_email:
        return None
    
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        return user
    except Exception as e:
        logger.error(f"Error getting user from token: {e}")
        return None
    finally:
        db.close()


async def authenticate_websocket(websocket: WebSocket) -> Optional[User]:
    """Authenticate WebSocket connection using token from query params or headers"""
    try:
        # Try to get token from query parameters first
        token = websocket.query_params.get("token")
        
        # If not in query params, try headers
        if not token:
            auth_header = websocket.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            logger.warning("No token provided in WebSocket connection")
            return None
        
        # Verify token and get user
        user = get_user_from_token(token)
        if not user:
            logger.warning("Invalid token in WebSocket connection")
            return None
        
        logger.info(f"WebSocket authenticated for user: {user.id}")
        return user
        
    except Exception as e:
        logger.error(f"Error authenticating WebSocket: {e}")
        return None


async def websocket_auth_middleware(websocket: WebSocket, call_next):
    """WebSocket authentication middleware"""
    user = await authenticate_websocket(websocket)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return
    
    # Add user to websocket state
    websocket.state.user = user
    await call_next(websocket)


class WebSocketAuthError(Exception):
    """Custom exception for WebSocket authentication errors"""
    def __init__(self, message: str, code: int = status.WS_1008_POLICY_VIOLATION):
        self.message = message
        self.code = code
        super().__init__(self.message)


def require_websocket_auth(websocket: WebSocket) -> User:
    """Require authentication for WebSocket connection"""
    if not hasattr(websocket.state, 'user') or not websocket.state.user:
        raise WebSocketAuthError("Authentication required")
    return websocket.state.user


def check_user_permissions(user: User, required_role: str = None) -> bool:
    """Check if user has required permissions"""
    if not user:
        return False
    
    if required_role:
        # Check if user has the required role
        if user.role.value != required_role and user.role.value != "admin":
            return False
    
    return True


async def authorize_room_access(user: User, room_id: int) -> bool:
    """Check if user has access to a specific chat room"""
    db: Session = SessionLocal()
    try:
        from app.models.chat import ChatRoomMember
        
        # Check if user is a member of the room
        membership = db.query(ChatRoomMember).filter(
            ChatRoomMember.user_id == user.id,
            ChatRoomMember.chat_room_id == room_id,
            ChatRoomMember.is_blocked == False
        ).first()
        
        return membership is not None
        
    except Exception as e:
        logger.error(f"Error checking room access for user {user.id}, room {room_id}: {e}")
        return False
    finally:
        db.close()


async def authorize_message_access(user: User, message_id: int) -> bool:
    """Check if user has access to a specific message"""
    db: Session = SessionLocal()
    try:
        from app.models.chat import Message, ChatRoomMember
        
        # Get the message and check room access
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return False
        
        # Check if user has access to the room containing the message
        return await authorize_room_access(user, message.chat_room_id)
        
    except Exception as e:
        logger.error(f"Error checking message access for user {user.id}, message {message_id}: {e}")
        return False
    finally:
        db.close()


class WebSocketPermissionChecker:
    """Helper class for checking WebSocket permissions"""
    
    def __init__(self, user: User):
        self.user = user
    
    async def can_send_message(self, room_id: int) -> bool:
        """Check if user can send messages in a room"""
        db: Session = SessionLocal()
        try:
            from app.models.chat import ChatRoomMember
            
            membership = db.query(ChatRoomMember).filter(
                ChatRoomMember.user_id == self.user.id,
                ChatRoomMember.chat_room_id == room_id
            ).first()
            
            if not membership or membership.is_blocked:
                return False
            
            return membership.can_send_messages
            
        except Exception as e:
            logger.error(f"Error checking send message permission: {e}")
            return False
        finally:
            db.close()
    
    async def can_send_media(self, room_id: int) -> bool:
        """Check if user can send media in a room"""
        db: Session = SessionLocal()
        try:
            from app.models.chat import ChatRoomMember
            
            membership = db.query(ChatRoomMember).filter(
                ChatRoomMember.user_id == self.user.id,
                ChatRoomMember.chat_room_id == room_id
            ).first()
            
            if not membership or membership.is_blocked:
                return False
            
            return membership.can_send_media
            
        except Exception as e:
            logger.error(f"Error checking send media permission: {e}")
            return False
        finally:
            db.close()
    
    async def can_manage_room(self, room_id: int) -> bool:
        """Check if user can manage a room"""
        db: Session = SessionLocal()
        try:
            from app.models.chat import ChatRoomMember
            
            membership = db.query(ChatRoomMember).filter(
                ChatRoomMember.user_id == self.user.id,
                ChatRoomMember.chat_room_id == room_id
            ).first()
            
            if not membership:
                return False
            
            return membership.role.value in ["admin", "owner", "moderator"]
            
        except Exception as e:
            logger.error(f"Error checking room management permission: {e}")
            return False
        finally:
            db.close()
    
    async def can_add_members(self, room_id: int) -> bool:
        """Check if user can add members to a room"""
        db: Session = SessionLocal()
        try:
            from app.models.chat import ChatRoomMember
            
            membership = db.query(ChatRoomMember).filter(
                ChatRoomMember.user_id == self.user.id,
                ChatRoomMember.chat_room_id == room_id
            ).first()
            
            if not membership:
                return False
            
            return membership.can_add_members
            
        except Exception as e:
            logger.error(f"Error checking add members permission: {e}")
            return False
        finally:
            db.close()
    
    async def can_pin_messages(self, room_id: int) -> bool:
        """Check if user can pin messages in a room"""
        db: Session = SessionLocal()
        try:
            from app.models.chat import ChatRoomMember
            
            membership = db.query(ChatRoomMember).filter(
                ChatRoomMember.user_id == self.user.id,
                ChatRoomMember.chat_room_id == room_id
            ).first()
            
            if not membership:
                return False
            
            return membership.can_pin_messages
            
        except Exception as e:
            logger.error(f"Error checking pin messages permission: {e}")
            return False
        finally:
            db.close()