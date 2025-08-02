from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatRoom, ChatRoomCreate, ChatRoomUpdate,
    Message, MessageCreate, MessageUpdate,
    MessageReaction, MessageReactionCreate,
    UserPresence, UserPresenceUpdate,
    MessageSearchQuery,
    ChatAnalytics
)
from app.controllers.chat import chat_controller

router = APIRouter()


# Chat Room Management
@router.post("/rooms", response_model=ChatRoom)
async def create_chat_room(
    room_data: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat room"""
    return await chat_controller.create_chat_room(room_data, current_user, db)


@router.get("/rooms", response_model=List[ChatRoom])
async def get_user_chat_rooms(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's chat rooms with pagination"""
    return await chat_controller.get_user_chat_rooms(page, size, current_user, db)


@router.get("/rooms/{room_id}", response_model=ChatRoom)
async def get_chat_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific chat room"""
    return await chat_controller.get_chat_room(room_id, current_user, db)


@router.put("/rooms/{room_id}", response_model=ChatRoom)
async def update_chat_room(
    room_id: int,
    room_data: ChatRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a chat room"""
    return await chat_controller.update_chat_room(room_id, room_data, current_user, db)


@router.delete("/rooms/{room_id}")
async def delete_chat_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a chat room (soft delete)"""
    return await chat_controller.delete_chat_room(room_id, current_user, db)


# Message Management
@router.post("/rooms/{room_id}/messages", response_model=Message)
async def send_message(
    room_id: int,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to a chat room"""
    return await chat_controller.send_message(room_id, message_data, current_user, db)


@router.get("/rooms/{room_id}/messages", response_model=List[Message])
async def get_messages(
    room_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages from a chat room"""
    return await chat_controller.get_messages(room_id, page, size, current_user, db)


@router.put("/messages/{message_id}", response_model=Message)
async def edit_message(
    message_id: int,
    message_data: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Edit a message"""
    return await chat_controller.edit_message(message_id, message_data, current_user, db)


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a message"""
    return await chat_controller.delete_message(message_id, current_user, db)


# File Upload for Messages
@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload an image for messages"""
    return await chat_controller.upload_image(file, current_user)


@router.post("/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload a file for messages"""
    return await chat_controller.upload_file(file, current_user)


@router.post("/upload/audio")
async def upload_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload an audio file for messages"""
    return await chat_controller.upload_audio(file, current_user)


# Reactions
@router.post("/messages/{message_id}/reactions", response_model=Optional[MessageReaction])
async def add_reaction(
    message_id: int,
    reaction_data: MessageReactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add or remove a reaction to a message"""
    return await chat_controller.add_reaction(message_id, reaction_data, current_user, db)


# Search
@router.post("/search", response_model=List[Message])
async def search_messages(
    search_query: MessageSearchQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search messages"""
    return await chat_controller.search_messages(search_query, current_user, db)


# User Presence
@router.get("/presence/{user_id}", response_model=UserPresence)
async def get_user_presence(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user presence status"""
    return await chat_controller.get_user_presence(user_id, current_user, db)


@router.put("/presence", response_model=UserPresence)
async def update_user_presence(
    presence_data: UserPresenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user presence status"""
    return await chat_controller.update_user_presence(presence_data, current_user, db)


# Room Members Management
@router.post("/rooms/{room_id}/members/{user_id}")
async def add_room_member(
    room_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a member to a chat room"""
    return await chat_controller.add_room_member(room_id, user_id, current_user, db)


@router.delete("/rooms/{room_id}/members/{user_id}")
async def remove_room_member(
    room_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from a chat room"""
    return await chat_controller.remove_room_member(room_id, user_id, current_user, db)


# Analytics
@router.get("/rooms/{room_id}/analytics", response_model=List[ChatAnalytics])
async def get_room_analytics(
    room_id: int,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get chat room analytics"""
    return await chat_controller.get_room_analytics(room_id, days, current_user, db)