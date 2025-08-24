# ERC Youth Management System

A comprehensive web application for managing youth activities, families, and church-related operations.

## Features

- User management and authentication
- Family and member management
- Activity tracking and analytics
- Document sharing and management
- Prayer chain management
- Chat and communication features
- Feedback and recommendation systems

## Logging System

The application uses a professional logging system instead of print statements for better debugging, monitoring, and production support.

### Logging Configuration

- **Location**: `app/core/logging_config.py`
- **Log Files**: Stored in the `logs/` directory
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Rotation**: Automatic log rotation with size limits (10MB) and backup counts

### Log Files

- `app_info.log` - General application information and warnings
- `app_error.log` - Error-level messages only
- `app_debug.log` - Detailed debug information (development mode)

### Usage

```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.debug("Debug information")
logger.info("General information")
logger.warning("Warning messages")
logger.error("Error messages", exc_info=True)  # Include stack trace
```

### Environment Variables

- `ENVIRONMENT`: Set to "production" for production logging levels
- Defaults to "development" for more verbose logging

### Benefits of Professional Logging

1. **Structured Output**: Consistent timestamp and format
2. **Log Levels**: Filter messages by importance
3. **File Rotation**: Automatic log management
4. **Production Ready**: Different configurations for dev/prod
5. **Debugging**: Stack traces and detailed error information
6. **Monitoring**: Easy to parse and analyze logs

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env`
4. Run the application: `python main.py`

## API Documentation

The application provides RESTful APIs for all major functionality. Access the interactive API documentation at `/docs` when running the application.
