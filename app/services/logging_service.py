from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.models.system_log import SystemLog
from app.models.user import User
from app.models.family import Family


class LoggingService:
    """Service for logging system activities"""
    
    @staticmethod
    def log_activity(
        db: Session,
        user: User,
        action: str,
        description: str,
        table_name: Optional[str] = None,
        record_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SystemLog:
        """
        Log a system activity
        
        Args:
            db: Database session
            user: User who performed the action
            action: Action type (CREATE, UPDATE, DELETE, LOGIN, etc.)
            description: Human-readable description of the action
            table_name: Name of the table affected
            record_id: ID of the record affected
            details: Additional context as dictionary
            ip_address: IP address of the user
            user_agent: User agent string
        """
        
        # Get family information
        family_id = None
        family_name = None
        family_category = None
        
        if user.family_id:
            family = db.query(Family).filter(Family.id == user.family_id).first()
            if family:
                family_id = family.id
                family_name = family.name
                family_category = family.category
        
        # Create log entry
        log_entry = SystemLog(
            user_id=user.id,
            user_name=user.full_name,
            family_id=family_id,
            family_name=family_name,
            family_category=family_category,
            action=action.upper(),
            description=description,
            table_name=table_name,
            record_id=record_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        return log_entry
    
    @staticmethod
    def get_action_description(action: str, table_name: str, operation: str = "performed") -> str:
        """
        Generate human-readable descriptions for common actions
        
        Args:
            action: Action type
            table_name: Name of the table
            operation: Operation verb (performed, created, updated, etc.)
        """
        descriptions = {
            "CREATE": f"Created new {table_name}",
            "UPDATE": f"Updated {table_name}",
            "DELETE": f"Deleted {table_name}",
            "LOGIN": "Logged into the system",
            "LOGOUT": "Logged out of the system",
            "REGISTER": f"Registered new {table_name}",
            "RESET_PASSWORD": "Reset password",
            "CHANGE_PASSWORD": "Changed password",
            "UPLOAD": f"Uploaded {table_name}",
            "DOWNLOAD": f"Downloaded {table_name}",
            "SHARE": f"Shared {table_name}",
            "JOIN": f"Joined {table_name}",
            "LEAVE": f"Left {table_name}",
            "APPROVE": f"Approved {table_name}",
            "REJECT": f"Rejected {table_name}",
            "SUBMIT": f"Submitted {table_name}",
            "PUBLISH": f"Published {table_name}",
            "ARCHIVE": f"Archived {table_name}",
            "RESTORE": f"Restored {table_name}",
            "BLOCK": f"Blocked user",
            "UNBLOCK": f"Unblocked user",
            "REPORT": f"Reported user",
            "PIN": f"Pinned message",
            "UNPIN": f"Unpinned message",
            "REACT": f"Reacted to message",
            "READ": f"Marked message as read",
            "SEND": f"Sent message",
            "CREATE_CHAT": "Created chat room",
            "JOIN_CHAT": "Joined chat room",
            "LEAVE_CHAT": "Left chat room",
            "ADD_MEMBER": "Added member to chat",
            "REMOVE_MEMBER": "Removed member from chat"
        }
        
        return descriptions.get(action.upper(), f"{operation} {action} on {table_name}")
    
    @staticmethod
    def log_user_creation(db: Session, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log user creation activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="CREATE",
            description=LoggingService.get_action_description("CREATE", "user account"),
            table_name="users",
            record_id=user.id,
            details={"email": user.email, "role": user.role.value if user.role else None},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_user_update(db: Session, user: User, updated_fields: list, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log user update activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="UPDATE",
            description=LoggingService.get_action_description("UPDATE", "user profile"),
            table_name="users",
            record_id=user.id,
            details={"updated_fields": updated_fields},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_user_login(db: Session, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log user login activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="LOGIN",
            description=LoggingService.get_action_description("LOGIN", "system"),
            table_name="users",
            record_id=user.id,
            details={"login_time": str(user.updated_at)},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_family_creation(db: Session, user: User, family: Family, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log family creation activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="CREATE",
            description=f"Created new family: {family.name} ({family.category})",
            table_name="families",
            record_id=family.id,
            details={"family_name": family.name, "family_category": family.category},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_announcement_creation(db: Session, user: User, announcement_id: int, title: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log announcement creation activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="CREATE",
            description=f"Created announcement: {title}",
            table_name="announcements",
            record_id=announcement_id,
            details={"announcement_title": title},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_document_upload(db: Session, user: User, document_id: int, filename: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log document upload activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="UPLOAD",
            description=f"Uploaded document: {filename}",
            table_name="family_documents",
            record_id=document_id,
            details={"filename": filename},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_prayer_chain_creation(db: Session, user: User, prayer_chain_id: int, title: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log prayer chain creation activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="CREATE",
            description=f"Created prayer chain: {title}",
            table_name="prayer_chains",
            record_id=prayer_chain_id,
            details={"prayer_chain_title": title},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_feedback_submission(db: Session, user: User, feedback_id: int, feedback_type: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log feedback submission activity"""
        return LoggingService.log_activity(
            db=db,
            user=user,
            action="SUBMIT",
            description=f"Submitted {feedback_type} feedback",
            table_name="feedback",
            record_id=feedback_id,
            details={"feedback_type": feedback_type},
            ip_address=ip_address,
            user_agent=user_agent
        )
