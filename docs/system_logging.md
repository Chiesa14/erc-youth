# System Logging Documentation

## Overview

The ERC Youth system implements comprehensive activity logging across all modules to track user actions, system events, and provide audit trails for compliance and debugging purposes.

## Architecture

### Components

1. **SystemLog Model** (`app/models/system_log.py`)
   - Database table to store all log entries
   - Contains user, family, action, and context information

2. **LoggingService** (`app/services/logging_service.py`)
   - Core service for creating and managing log entries
   - Provides predefined methods for common operations

3. **Logging Decorators** (`app/utils/logging_decorator.py`)
   - Decorators that automatically log function calls
   - Applied to controller functions for seamless logging

4. **Logging Middleware** (`app/core/logging_middleware.py`)
   - HTTP request/response logging
   - Automatic IP and user agent extraction

## Schema

### SystemLog Table Structure

```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    user_name VARCHAR NOT NULL,
    family_id INTEGER REFERENCES families(id),
    family_name VARCHAR,
    family_category VARCHAR,
    action VARCHAR NOT NULL,
    description TEXT NOT NULL,
    table_name VARCHAR,
    record_id INTEGER,
    details JSON,
    ip_address VARCHAR,
    user_agent VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `user_id` | Integer | ID of user who performed the action |
| `user_name` | String | Full name of the user |
| `family_id` | Integer | ID of user's family (optional) |
| `family_name` | String | Name of the family |
| `family_category` | String | Category of the family |
| `action` | String | Action type (CREATE, UPDATE, DELETE, etc.) |
| `description` | Text | Human-readable description |
| `table_name` | String | Database table affected |
| `record_id` | Integer | ID of the affected record |
| `details` | JSON | Additional context and metadata |
| `ip_address` | String | User's IP address |
| `user_agent` | String | User's browser/client information |
| `created_at` | Timestamp | When the action occurred |

## Logging Coverage

### Modules with Complete Logging

✅ **Users** - Account creation, updates, authentication
✅ **Families** - CRUD operations, member management  
✅ **Announcements** - Create, update, delete, view, flyer operations
✅ **Chat** - Rooms, messages, uploads, member management
✅ **Feedback** - Submissions, replies, status updates
✅ **Prayer Chains** - CRUD operations, schedule management
✅ **Family Members** - CRUD, permissions, invitations
✅ **Family Activities** - Creation and viewing
✅ **Family Documents** - Upload, download, deletion
✅ **Shared Documents** - Full document lifecycle
✅ **Recommendations** - Programs, comments, approvals

### Action Types

- **CREATE** - New record creation
- **UPDATE** - Record modification  
- **DELETE** - Record deletion
- **VIEW** - Data retrieval/viewing
- **UPLOAD** - File uploads
- **DOWNLOAD** - File downloads
- **LOGIN** - User authentication
- **LOGOUT** - Session termination

## Usage

### Using Decorators (Recommended)

```python
from app.utils.logging_decorator import log_create, log_update, log_delete, log_view

@log_create("announcements", "Created new announcement")
def create_announcement(db: Session, announcement: AnnouncementCreate, current_user: User):
    # Function implementation
    return created_announcement

@log_update("users", "Updated user profile")  
def update_user_profile(db: Session, user: User, updates: UserUpdate):
    # Function implementation
    return updated_user
```

### Direct Service Usage

```python
from app.services.logging_service import LoggingService

LoggingService.log_activity(
    db=db,
    user=current_user,
    action="CUSTOM_ACTION",
    description="Custom activity description",
    table_name="custom_table",
    record_id=123,
    details={"custom": "metadata"},
    ip_address="127.0.0.1",
    user_agent="CustomClient/1.0"
)
```

### Predefined Logging Methods

```python
# User operations
LoggingService.log_user_creation(db, user, ip_address, user_agent)
LoggingService.log_user_login(db, user, ip_address, user_agent)

# Family operations  
LoggingService.log_family_creation(db, user, family, ip_address, user_agent)

# Document operations
LoggingService.log_document_upload(db, user, doc_id, filename, ip_address, user_agent)

# Feedback operations
LoggingService.log_feedback_submission(db, user, feedback_id, type, ip_address, user_agent)
```

## Security and Privacy

### PII Protection

The logging system automatically handles PII (Personally Identifiable Information) protection:

- **Never logged**: Passwords, tokens, API keys, sensitive personal data
- **Redacted**: Email addresses in certain contexts
- **Hashed**: Temporary passwords and access codes
- **Sanitized**: User input that might contain sensitive data

### Data Retention

- Log entries are retained indefinitely for audit purposes
- Implement log rotation for performance (recommended)
- Consider archiving old logs based on compliance requirements

## Performance Considerations

### Asynchronous Logging

- Logging operations are designed to be non-blocking
- Database operations use connection pooling
- Failed logging attempts don't interrupt business logic

### Sampling

- Consider implementing sampling for high-frequency operations
- Use batch logging for bulk operations
- Monitor log volume and storage requirements

### Indexing

Recommended database indexes for performance:

```sql
CREATE INDEX idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX idx_system_logs_family_id ON system_logs(family_id);
CREATE INDEX idx_system_logs_action ON system_logs(action);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_table_name ON system_logs(table_name);
```

## Monitoring and Alerting

### Key Metrics

- Log entry volume per hour/day
- Failed logging attempts
- Most active users/families
- Most common actions
- Error rates by module

### Queries for Monitoring

```python
# Recent activity
recent_logs = db.query(SystemLog).filter(
    SystemLog.created_at >= datetime.now() - timedelta(hours=24)
).count()

# User activity summary
user_activity = db.query(
    SystemLog.user_name, 
    func.count(SystemLog.id)
).group_by(SystemLog.user_name).all()

# Error tracking (if using structured details)
error_logs = db.query(SystemLog).filter(
    SystemLog.details.contains({"error": True})
).all()
```

## Testing

### Running Tests

```bash
# Run comprehensive logging tests
python tests/test_system_logs_comprehensive.py

# Run integration tests  
python tests/test_logging_integration.py
```

### Test Coverage

The test suite covers:
- All logging decorators
- Error handling scenarios
- Edge cases (missing user, database errors)
- Schema compatibility
- Integration with all modules

## Troubleshooting

### Common Issues

**Logging not working:**
1. Check database connectivity
2. Verify user object has required fields
3. Check decorator application
4. Review error logs

**Performance issues:**
1. Check database indexes
2. Monitor log volume
3. Consider async processing
4. Review query patterns

**Missing context:**
1. Ensure user is passed to functions
2. Check middleware configuration  
3. Verify request context propagation

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('app.services.logging_service').setLevel(logging.DEBUG)
```

## Migration Notes

### From Previous Logging

If migrating from a different logging system:

1. Map existing log formats to new schema
2. Update log queries and reports
3. Migrate historical data if required
4. Update monitoring dashboards

### Schema Changes

The current schema is backward compatible. Future changes should:

1. Add new fields as nullable
2. Create migration scripts
3. Update all affected queries
4. Test with existing data

## Examples

### Complete Announcement Logging

```python
# app/controllers/announcement.py

@log_create("announcements", "Created new announcement")
async def create_announcement(
    announcement: AnnouncementCreate,
    flyer: Optional[UploadFile],
    db: Session,
    current_user: User
) -> AnnouncementOut:
    """Create a new announcement with automatic logging"""
    # Implementation creates announcement
    # Decorator automatically logs:
    # - User: current_user.full_name
    # - Action: CREATE
    # - Description: "Created new announcement"
    # - Table: announcements
    # - Record ID: announcement.id
    return created_announcement
```

### Chat Operations Logging

```python
# app/controllers/chat.py

class ChatController:
    @log_create("chat_rooms", "Created new chat room")
    async def create_chat_room(self, room_data: ChatRoomCreate, current_user: User, db: Session):
        """Create chat room with logging"""
        return created_room
    
    @log_create("messages", "Sent chat message")
    async def send_message(self, room_id: int, message_data: MessageCreate, current_user: User, db: Session):
        """Send message with logging"""  
        return sent_message
```

## Best Practices

1. **Consistent Naming**: Use consistent action names and descriptions
2. **Meaningful Context**: Include relevant details in the `details` JSON field
3. **Error Handling**: Don't let logging failures break business logic
4. **Performance**: Monitor log volume and query performance
5. **Security**: Never log sensitive information
6. **Testing**: Test all logging scenarios including edge cases

## API Integration

### Retrieving Logs

```python
# app/api/endpoints/system_logs.py

@router.get("/system-logs", response_model=List[SystemLogResponse])
async def get_system_logs(
    filter: SystemLogFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get filtered system logs"""
    query = db.query(SystemLog)
    
    if filter.user_id:
        query = query.filter(SystemLog.user_id == filter.user_id)
    if filter.action:
        query = query.filter(SystemLog.action == filter.action)
    if filter.start_date:
        query = query.filter(SystemLog.created_at >= filter.start_date)
        
    return query.offset(filter.skip).limit(filter.limit).all()
```

## Conclusion

The system logging implementation provides comprehensive audit trails, debugging capabilities, and compliance support across all ERC Youth modules. The decorator-based approach ensures consistency while the flexible schema accommodates various types of activities and contexts.

For questions or issues, refer to the troubleshooting section or contact the development team.