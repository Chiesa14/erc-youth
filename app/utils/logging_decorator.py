from functools import wraps
from typing import Optional, Callable, Any
from sqlalchemy.orm import Session
from app.services.logging_service import LoggingService
import logging

# Enhanced logging decorators for comprehensive system activity tracking
# These decorators automatically capture user context, request info, and structured data

logger = logging.getLogger(__name__)


def log_activity(
    action: str,
    description: Optional[str] = None,
    table_name: Optional[str] = None,
    get_record_id: Optional[Callable] = None,
    get_details: Optional[Callable] = None,
    get_ip_address: Optional[Callable] = None,
    get_user_agent: Optional[Callable] = None
):
    """
    Decorator to log activities in controller functions
    
    Args:
        action: Action type (CREATE, UPDATE, DELETE, etc.)
        description: Custom description or callable that returns description
        table_name: Table name or callable that returns table name
        get_record_id: Function to extract record ID from function result
        get_details: Function to extract additional details
        get_ip_address: Function to extract IP address from request
        get_user_agent: Function to extract user agent from request
    """
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            try:
                # Extract database session and user from function arguments
                db = None
                user = None
                request = None
                
                for arg in args:
                    if hasattr(arg, '__class__') and 'Session' in str(arg.__class__):
                        db = arg
                    elif hasattr(arg, '__class__') and 'User' in str(arg.__class__):
                        user = arg
                    elif hasattr(arg, '__class__') and 'Request' in str(arg.__class__):
                        request = arg
                
                # Also check kwargs
                if not db and 'db' in kwargs:
                    db = kwargs['db']
                if not user and 'user' in kwargs:
                    user = kwargs['user']
                if not request and 'request' in kwargs:
                    request = kwargs['request']
                
                # If we have the required components, log the activity
                if db and user:
                    # Generate description
                    final_description = description
                    if callable(description):
                        try:
                            final_description = description(result, *args, **kwargs)
                        except Exception as e:
                            logger.warning(f"Failed to generate description: {e}")
                            final_description = f"Performed {action.lower()} action"
                    
                    # Generate table name
                    final_table_name = table_name
                    if callable(table_name):
                        try:
                            final_table_name = table_name(result, *args, **kwargs)
                        except Exception as e:
                            logger.warning(f"Failed to generate table name: {e}")
                            final_table_name = None
                    
                    # Extract record ID
                    record_id = None
                    if get_record_id:
                        try:
                            record_id = get_record_id(result, *args, **kwargs)
                        except Exception as e:
                            logger.warning(f"Failed to extract record ID: {e}")
                    
                    # Extract additional details
                    details = None
                    if get_details:
                        try:
                            details = get_details(result, *args, **kwargs)
                        except Exception as e:
                            logger.warning(f"Failed to extract details: {e}")
                    
                    # Extract IP address
                    ip_address = None
                    if get_ip_address and request:
                        try:
                            ip_address = get_ip_address(request)
                        except Exception as e:
                            logger.warning(f"Failed to extract IP address: {e}")
                    
                    # Extract user agent
                    user_agent = None
                    if get_user_agent and request:
                        try:
                            user_agent = get_user_agent(request)
                        except Exception as e:
                            logger.warning(f"Failed to extract user agent: {e}")
                    
                    # Log the activity
                    LoggingService.log_activity(
                        db=db,
                        user=user,
                        action=action,
                        description=final_description or f"Performed {action.lower()} action",
                        table_name=final_table_name,
                        record_id=record_id,
                        details=details,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
            except Exception as e:
                logger.error(f"Failed to log activity for {func.__name__}: {e}")
            
            return result
        
        return wrapper
    
    return decorator


# Helper functions for common use cases
def extract_id_from_result(result, *args, **kwargs):
    """Extract ID from function result"""
    if hasattr(result, 'id'):
        return result.id
    elif isinstance(result, dict) and 'id' in result:
        return result['id']
    elif isinstance(result, (list, tuple)) and len(result) > 0:
        first_item = result[0]
        if hasattr(first_item, 'id'):
            return first_item.id
        elif isinstance(first_item, dict) and 'id' in first_item:
            return first_item['id']
    return None


def extract_ip_from_request(request):
    """Extract IP address from request"""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def extract_user_agent_from_request(request):
    """Extract user agent from request"""
    return request.headers.get("user-agent", "")


# Predefined decorators for common actions
# These provide standardized logging for the most common CRUD operations
def log_create(table_name: str, description: Optional[str] = None):
    """
    Decorator for CREATE operations
    
    Usage:
        @log_create("announcements", "Created new announcement")
        def create_announcement(db, current_user, ...):
            return created_item
    """
    return log_activity(
        action="CREATE",
        description=description or f"Created new {table_name}",
        table_name=table_name,
        get_record_id=extract_id_from_result,
        get_ip_address=extract_ip_from_request,
        get_user_agent=extract_user_agent_from_request
    )


def log_update(table_name: str, description: Optional[str] = None):
    """
    Decorator for UPDATE operations
    
    Usage:
        @log_update("users", "Updated user profile")
        def update_user(db, current_user, ...):
            return updated_item
    """
    return log_activity(
        action="UPDATE",
        description=description or f"Updated {table_name}",
        table_name=table_name,
        get_record_id=extract_id_from_result,
        get_ip_address=extract_ip_from_request,
        get_user_agent=extract_user_agent_from_request
    )


def log_delete(table_name: str, description: Optional[str] = None):
    """
    Decorator for DELETE operations
    
    Usage:
        @log_delete("documents", "Deleted document")
        def delete_document(db, current_user, doc_id):
            return success_status
    """
    return log_activity(
        action="DELETE",
        description=description or f"Deleted {table_name}",
        table_name=table_name,
        get_record_id=extract_id_from_result,
        get_ip_address=extract_ip_from_request,
        get_user_agent=extract_user_agent_from_request
    )


def log_view(table_name: str, description: Optional[str] = None):
    """
    Decorator for VIEW operations
    
    Usage:
        @log_view("families", "Viewed family details")
        def get_family_by_id(db, current_user, family_id):
            return family_data
    """
    return log_activity(
        action="VIEW",
        description=description or f"Viewed {table_name}",
        table_name=table_name,
        get_ip_address=extract_ip_from_request,
        get_user_agent=extract_user_agent_from_request
    )


def log_login(description: str = "User logged into the system"):
    """Decorator for login operations"""
    return log_activity(
        action="LOGIN",
        description=description,
        table_name="users",
        get_ip_address=extract_ip_from_request,
        get_user_agent=extract_user_agent_from_request
    )


def log_upload(table_name: str, description: Optional[str] = None):
    """
    Decorator for file upload operations
    
    Usage:
        @log_upload("documents", "Uploaded family document")
        def upload_document(db, current_user, file):
            return uploaded_doc
    """
    return log_activity(
        action="UPLOAD",
        description=description or f"Uploaded {table_name}",
        table_name=table_name,
        get_record_id=extract_id_from_result,
        get_ip_address=extract_ip_from_request,
        get_user_agent=extract_user_agent_from_request
    )
