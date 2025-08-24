from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # User who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_name = Column(String, nullable=False)  # Full name of the user
    
    # Family information
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True)
    family_name = Column(String, nullable=True)
    family_category = Column(String, nullable=True)
    
    # Action details
    action = Column(String, nullable=False)  # e.g., "CREATE", "UPDATE", "DELETE", "LOGIN", etc.
    description = Column(Text, nullable=False)  # Human-readable description
    table_name = Column(String, nullable=True)  # Which table was affected
    record_id = Column(Integer, nullable=True)  # ID of the affected record
    
    # Additional context
    details = Column(JSON, nullable=True)  # Store additional context as JSON
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="system_logs")
    family = relationship("Family", backref="system_logs")
