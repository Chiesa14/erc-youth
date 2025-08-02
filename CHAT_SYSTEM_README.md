# ERC Youth Real-Time Chat System

A comprehensive real-time chat system built with FastAPI, WebSockets, and modern web technologies. This system provides instant messaging, file sharing, voice messages, and many advanced features for the ERC Youth community.

## 🚀 Features

### Core Messaging
- ✅ **Real-time messaging** with WebSocket connections
- ✅ **Typing indicators** with user presence detection
- ✅ **Message status indicators** (sent/delivered/read receipts)
- ✅ **Message reactions** and emoji support
- ✅ **Reply-to-message** threading functionality
- ✅ **Message editing and deletion** with edit history
- ✅ **Message search and filtering** capabilities
- ✅ **Message pagination** and infinite scroll

### File & Media Support
- ✅ **File upload** with drag-and-drop support
- ✅ **Image sharing** with thumbnail generation and preview
- ✅ **Audio message** recording and playback with waveform visualization
- ✅ **Voice-to-text transcription** for audio messages
- ✅ **Video sharing** with thumbnail generation
- ✅ **File type validation** and size limits

### User Management & Security
- ✅ **User authentication** for WebSocket connections
- ✅ **User online/offline status** with last seen timestamps
- ✅ **User roles and permissions** system
- ✅ **Message encryption** for security
- ✅ **User blocking and reporting** features

### Chat Rooms & Groups
- ✅ **Chat room creation** and management
- ✅ **Admin controls** for room management
- ✅ **Group chat support** with member management
- ✅ **User permissions** (send messages, add members, etc.)
- ✅ **Room analytics** and statistics

### Advanced Features
- ✅ **Push notifications** for offline users
- ✅ **Message scheduling** for delayed sending
- ✅ **Auto-delete messages** with timer options
- ✅ **Message pinning** for important announcements
- ✅ **Comprehensive error handling** with reconnection logic

### Planned Features
- 🔄 Message forwarding between chats
- 🔄 Chat backup and export functionality
- 🔄 Custom themes and chat customization options
- 🔄 External services integration (GIFs, stickers)
- 🔄 Markdown formatting for rich text messages
- 🔄 Location sharing capabilities
- 🔄 Contact sharing functionality
- 🔄 Chat translation services

## 🏗️ Architecture

### Backend Components

#### Models (`app/models/chat.py`)
- **ChatRoom**: Chat room/group management
- **ChatRoomMember**: User membership and permissions
- **Message**: Core message entity with all message types
- **MessageReaction**: Emoji reactions on messages
- **MessageEditHistory**: Track message edit history
- **MessageReadReceipt**: Read receipt tracking
- **UserPresence**: Online/offline status tracking
- **PinnedMessage**: Pinned messages in rooms
- **UserBlock**: User blocking functionality
- **UserReport**: User reporting system
- **ChatAnalytics**: Chat statistics and analytics

#### Services
- **ChatService** (`app/services/chat_service.py`): Core business logic
- **FileUploadService** (`app/services/file_upload.py`): File handling and processing
- **EncryptionService** (`app/services/encryption_service.py`): Message encryption
- **NotificationService** (`app/services/notification_service.py`): Push notifications

#### WebSocket Management
- **ConnectionManager** (`app/core/websocket_manager.py`): WebSocket connection handling
- **WebSocket Authentication** (`app/core/websocket_auth.py`): Secure WebSocket connections

#### API Routes
- **Chat REST API** (`app/api/routes/chat.py`): HTTP endpoints for chat operations
- **WebSocket Routes** (`app/api/routes/websocket.py`): WebSocket endpoints and test interface

### Database Schema

```sql
-- Core chat tables
ChatRooms (id, name, type, settings, encryption, timestamps)
ChatRoomMembers (user_id, room_id, role, permissions, status)
Messages (id, room_id, sender_id, content, type, metadata, timestamps)
MessageReactions (message_id, user_id, emoji, timestamp)
MessageEditHistory (message_id, old_content, timestamp)
MessageReadReceipts (message_id, user_id, read_at)
UserPresence (user_id, is_online, last_seen, status_message)
PinnedMessages (room_id, message_id, pinned_by, timestamp)
UserBlocks (blocker_id, blocked_id, reason, timestamp)
UserReports (reporter_id, reported_id, message_id, reason, status)
ChatAnalytics (room_id, date, message_stats, user_stats)
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Redis (optional, for advanced features)

### Installation

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set up environment variables** (`.env`):
```env
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

3. **Run database migrations**:
```bash
# The application will automatically create tables on startup
python main.py
```

4. **Start the server**:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing the Chat System

1. **Access the test interface**:
   - Open `http://localhost:8000/static/chat.html` in your browser
   - Login with existing user credentials
   - Start chatting!

2. **WebSocket test page**:
   - Visit `http://localhost:8000/chat/ws/test` for WebSocket testing
   - Use JWT tokens for authentication

3. **API documentation**:
   - FastAPI auto-generated docs: `http://localhost:8000/docs`
   - ReDoc documentation: `http://localhost:8000/redoc`

## 📡 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `GET /users/me` - Get current user info

### Chat Rooms
- `GET /chat/rooms` - Get user's chat rooms
- `POST /chat/rooms` - Create new chat room
- `GET /chat/rooms/{room_id}` - Get specific room
- `PUT /chat/rooms/{room_id}` - Update room settings
- `DELETE /chat/rooms/{room_id}` - Delete room

### Messages
- `GET /chat/rooms/{room_id}/messages` - Get room messages
- `POST /chat/rooms/{room_id}/messages` - Send message
- `PUT /chat/messages/{message_id}` - Edit message
- `DELETE /chat/messages/{message_id}` - Delete message

### File Uploads
- `POST /chat/upload/image` - Upload image
- `POST /chat/upload/audio` - Upload audio
- `POST /chat/upload/file` - Upload general file

### Reactions & Interactions
- `POST /chat/messages/{message_id}/reactions` - Add/remove reaction
- `POST /chat/search` - Search messages

### Room Management
- `POST /chat/rooms/{room_id}/members/{user_id}` - Add member
- `DELETE /chat/rooms/{room_id}/members/{user_id}` - Remove member
- `GET /chat/rooms/{room_id}/analytics` - Get room analytics

### User Presence
- `GET /chat/presence/{user_id}` - Get user presence
- `PUT /chat/presence` - Update presence status

## 🔌 WebSocket Events

### Client to Server
```javascript
// Join a room
ws.send(JSON.stringify({
    type: 'join_room',
    data: { room_id: 123 }
}));

// Send typing indicator
ws.send(JSON.stringify({
    type: 'typing',
    data: { room_id: 123, is_typing: true }
}));

// Ping server
ws.send(JSON.stringify({
    type: 'ping',
    data: {}
}));
```

### Server to Client
```javascript
// New message received
{
    type: 'new_message',
    data: {
        message_id: 456,
        chat_room_id: 123,
        sender_id: 789,
        sender_name: 'John Doe',
        content: 'Hello world!',
        message_type: 'text',
        created_at: '2024-01-01T12:00:00Z'
    }
}

// Typing indicator
{
    type: 'typing_indicator',
    data: {
        user_id: 789,
        room_id: 123,
        is_typing: true,
        timestamp: '2024-01-01T12:00:00Z'
    }
}

// Presence update
{
    type: 'presence_update',
    data: {
        user_id: 789,
        is_online: true,
        last_seen: '2024-01-01T12:00:00Z'
    }
}
```

## 🔒 Security Features

### Message Encryption
- **End-to-end encryption** for sensitive rooms
- **Room-specific encryption keys**
- **Automatic key rotation** support
- **Encrypted file storage**

### Authentication & Authorization
- **JWT-based authentication** for both HTTP and WebSocket
- **Role-based access control** (RBAC)
- **Permission-based room access**
- **User blocking and reporting**

### Data Protection
- **Input validation** and sanitization
- **File type and size validation**
- **Rate limiting** (can be added)
- **CORS protection**

## 📊 Monitoring & Analytics

### Chat Analytics
- **Message statistics** (total, by type, by user)
- **User activity** tracking
- **Room engagement** metrics
- **File sharing** statistics

### System Monitoring
- **WebSocket connection** tracking
- **Online user** counting
- **Room membership** statistics
- **Error logging** and tracking

## 🎨 Frontend Integration

### JavaScript Client Example
```javascript
// Connect to WebSocket
const ws = new WebSocket(`ws://localhost:8000/chat/ws?token=${token}`);

// Handle messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
};

// Send message via REST API
fetch('/chat/rooms/123/messages', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        content: 'Hello world!',
        message_type: 'text'
    })
});
```

### React Integration
```jsx
import { useState, useEffect } from 'react';

function ChatComponent() {
    const [ws, setWs] = useState(null);
    const [messages, setMessages] = useState([]);

    useEffect(() => {
        const websocket = new WebSocket(`ws://localhost:8000/chat/ws?token=${token}`);
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'new_message') {
                setMessages(prev => [...prev, data.data]);
            }
        };
        setWs(websocket);

        return () => websocket.close();
    }, []);

    return (
        <div className="chat-container">
            {/* Chat UI components */}
        </div>
    );
}
```

## 🧪 Testing

### Manual Testing
1. Use the provided HTML interface at `/static/chat.html`
2. Test WebSocket connections at `/chat/ws/test`
3. Use API documentation at `/docs` for endpoint testing

### Automated Testing (Planned)
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

## 🚀 Deployment

### Production Setup
1. **Environment Configuration**:
```env
DATABASE_URL=postgresql://prod_user:password@db_host/prod_db
SECRET_KEY=production-secret-key
REDIS_URL=redis://redis_host:6379/0
```

2. **Docker Deployment**:
```dockerfile
FROM python:3.9-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

3. **Nginx Configuration**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation at `/docs`

## 🔄 Changelog

### Version 1.0.0 (Current)
- ✅ Complete real-time chat system
- ✅ File upload and media sharing
- ✅ User presence and typing indicators
- ✅ Message encryption and security
- ✅ Room management and permissions
- ✅ Push notifications
- ✅ Analytics and monitoring

### Planned Updates
- 🔄 Mobile app integration
- 🔄 Advanced moderation tools
- 🔄 Integration with external services
- 🔄 Performance optimizations
- 🔄 Advanced analytics dashboard