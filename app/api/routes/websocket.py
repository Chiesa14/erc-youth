import json
import uuid
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from app.core.websocket_manager import connection_manager
from app.core.websocket_auth import authenticate_websocket, WebSocketPermissionChecker
from app.models.user import User
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat connections"""
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # Authenticate the connection
        user = await authenticate_websocket(websocket)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return
        
        # Connect to the manager
        await connection_manager.connect(websocket, user.id, connection_id)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {
                "user_id": user.id,
                "connection_id": connection_id,
                "message": "Connected successfully"
            }
        }))
        
        # Listen for messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle the message
                await connection_manager.handle_message(websocket, user.id, connection_id, message_data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.id}")
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from user {user.id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message for user {user.id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Internal server error"}
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during setup for user {user.id if user else 'unknown'}")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket endpoint: {e}")
    finally:
        # Clean up connection
        if user:
            await connection_manager.disconnect(user.id, connection_id)


@router.websocket("/ws/room/{room_id}")
async def websocket_room_endpoint(websocket: WebSocket, room_id: int):
    """WebSocket endpoint for direct room connections"""
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # Authenticate the connection
        user = await authenticate_websocket(websocket)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
            return
        
        # Check room access permissions
        from app.core.websocket_auth import authorize_room_access
        if not await authorize_room_access(user, room_id):
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="Access denied to room")
            return
        
        # Connect to the manager
        await connection_manager.connect(websocket, user.id, connection_id)
        
        # Join the specific room
        await connection_manager.join_room(user.id, room_id, connection_id)
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "room_connection_established",
            "data": {
                "user_id": user.id,
                "room_id": room_id,
                "connection_id": connection_id,
                "message": f"Connected to room {room_id}"
            }
        }))
        
        # Listen for messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Add room context to message
                if "data" not in message_data:
                    message_data["data"] = {}
                message_data["data"]["room_id"] = room_id
                
                # Handle the message
                await connection_manager.handle_message(websocket, user.id, connection_id, message_data)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.id} in room {room_id}")
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from user {user.id} in room {room_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }))
            except Exception as e:
                logger.error(f"Error handling WebSocket message for user {user.id} in room {room_id}: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": "Internal server error"}
                }))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during setup for user {user.id if user else 'unknown'} in room {room_id}")
    except Exception as e:
        logger.error(f"Unexpected error in room WebSocket endpoint: {e}")
    finally:
        # Clean up connection
        if user:
            await connection_manager.disconnect(user.id, connection_id)


@router.get("/ws/test")
async def websocket_test_page():
    """Test page for WebSocket connections"""
    # Inject the WebSocket URL from settings
    websocket_url = settings.websocket_chat_url
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .message-box { 
                border: 1px solid #ccc; 
                height: 300px; 
                overflow-y: scroll; 
                padding: 10px; 
                margin: 10px 0; 
                background: #f9f9f9;
            }
            .input-group { margin: 10px 0; }
            .input-group input, .input-group select, .input-group button { 
                margin: 5px; 
                padding: 8px; 
            }
            .message { 
                margin: 5px 0; 
                padding: 5px; 
                border-left: 3px solid #007bff; 
                background: white;
            }
            .error { border-left-color: #dc3545; }
            .success { border-left-color: #28a745; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>WebSocket Chat Test</h1>
            
            <div class="input-group">
                <input type="text" id="token" placeholder="JWT Token" style="width: 300px;">
                <button onclick="connect()">Connect</button>
                <button onclick="disconnect()">Disconnect</button>
                <span id="status">Disconnected</span>
            </div>
            
            <div class="input-group">
                <input type="number" id="roomId" placeholder="Room ID">
                <button onclick="joinRoom()">Join Room</button>
                <button onclick="leaveRoom()">Leave Room</button>
            </div>
            
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="Type a message..." style="width: 400px;">
                <button onclick="sendMessage()">Send Message</button>
            </div>
            
            <div class="input-group">
                <button onclick="startTyping()">Start Typing</button>
                <button onclick="stopTyping()">Stop Typing</button>
                <button onclick="sendPing()">Send Ping</button>
            </div>
            
            <div class="message-box" id="messages"></div>
        </div>

        <script>
            let ws = null;
            let currentRoomId = null;
            
            function addMessage(message, type = 'info') {
                const messagesDiv = document.getElementById('messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${type}`;
                messageDiv.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong>: ${message}`;
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
            
            function connect() {
                const token = document.getElementById('token').value;
                if (!token) {
                    addMessage('Please enter a JWT token', 'error');
                    return;
                }
                
                const wsUrl = `WS_URL_PLACEHOLDER?token=${encodeURIComponent(token)}`;
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    document.getElementById('status').textContent = 'Connected';
                    addMessage('Connected to WebSocket', 'success');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage(`Received: ${JSON.stringify(data, null, 2)}`);
                };
                
                ws.onclose = function(event) {
                    document.getElementById('status').textContent = 'Disconnected';
                    addMessage(`Connection closed: ${event.code} - ${event.reason}`, 'error');
                };
                
                ws.onerror = function(error) {
                    addMessage(`WebSocket error: ${error}`, 'error');
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            
            function joinRoom() {
                const roomId = parseInt(document.getElementById('roomId').value);
                if (!roomId || !ws) return;
                
                currentRoomId = roomId;
                ws.send(JSON.stringify({
                    type: 'join_room',
                    data: { room_id: roomId }
                }));
                addMessage(`Joining room ${roomId}`, 'success');
            }
            
            function leaveRoom() {
                if (!currentRoomId || !ws) return;
                
                ws.send(JSON.stringify({
                    type: 'leave_room',
                    data: { room_id: currentRoomId }
                }));
                addMessage(`Leaving room ${currentRoomId}`, 'success');
                currentRoomId = null;
            }
            
            function sendMessage() {
                const message = document.getElementById('messageInput').value;
                if (!message || !ws) return;
                
                ws.send(JSON.stringify({
                    type: 'message',
                    data: {
                        content: message,
                        room_id: currentRoomId
                    }
                }));
                
                document.getElementById('messageInput').value = '';
                addMessage(`Sent: ${message}`, 'success');
            }
            
            function startTyping() {
                if (!currentRoomId || !ws) return;
                
                ws.send(JSON.stringify({
                    type: 'typing',
                    data: {
                        room_id: currentRoomId,
                        is_typing: true
                    }
                }));
                addMessage('Started typing indicator', 'success');
            }
            
            function stopTyping() {
                if (!currentRoomId || !ws) return;
                
                ws.send(JSON.stringify({
                    type: 'typing',
                    data: {
                        room_id: currentRoomId,
                        is_typing: false
                    }
                }));
                addMessage('Stopped typing indicator', 'success');
            }
            
            function sendPing() {
                if (!ws) return;
                
                ws.send(JSON.stringify({
                    type: 'ping',
                    data: {}
                }));
                addMessage('Sent ping', 'success');
            }
            
            // Handle Enter key in message input
            document.getElementById('messageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """
    
    # Replace the placeholder with the actual WebSocket URL
    html_content = html_content.replace("WS_URL_PLACEHOLDER", websocket_url)
    
    return HTMLResponse(content=html_content)


@router.get("/ws/stats")
async def websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "online_users": list(connection_manager.get_online_users()),
        "total_online": len(connection_manager.get_online_users()),
        "active_rooms": len(connection_manager.room_members),
        "room_stats": {
            room_id: len(members) 
            for room_id, members in connection_manager.room_members.items()
        },
        "typing_indicators": {
            room_id: list(users.keys())
            for room_id, users in connection_manager.typing_indicators.items()
        }
    }


@router.post("/ws/broadcast/{room_id}")
async def broadcast_to_room(room_id: int, message: Dict[str, Any]):
    """Broadcast a message to all users in a room (admin only)"""
    await connection_manager.broadcast_to_room(room_id, {
        "type": "broadcast",
        "data": message
    })
    return {"message": f"Broadcast sent to room {room_id}"}


@router.post("/ws/notify/{user_id}")
async def notify_user(user_id: int, message: Dict[str, Any]):
    """Send a notification to a specific user (admin only)"""
    await connection_manager.send_personal_message(user_id, {
        "type": "notification",
        "data": message
    })
    return {"message": f"Notification sent to user {user_id}"}