"""
Middleware for automatic timestamp management in SQLAlchemy models.
"""

from datetime import datetime, timezone
from sqlalchemy import event, DateTime, Column
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta
from typing import Any


def utc_now():
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


class TimestampMiddleware:
    """Middleware to automatically manage createdAt and updatedAt timestamps"""
    
    @staticmethod
    def setup_timestamp_listeners():
        """Set up SQLAlchemy event listeners for automatic timestamp management"""
        
        @event.listens_for(Session, 'before_insert')
        def receive_before_insert(mapper, connection, target):
            """Set created_at and updated_at before insert"""
            if hasattr(target, 'created_at') and target.created_at is None:
                target.created_at = utc_now()
            if hasattr(target, 'updated_at') and target.updated_at is None:
                target.updated_at = utc_now()
        
        @event.listens_for(Session, 'before_update')
        def receive_before_update(mapper, connection, target):
            """Set updated_at before update"""
            if hasattr(target, 'updated_at'):
                target.updated_at = utc_now()



def add_timestamp_columns(cls):
    """
    Class decorator to add timestamp columns to SQLAlchemy models.
    This is a fallback for models that don't have timestamp columns yet.
    """
    if not hasattr(cls, 'created_at'):
        cls.created_at = Column(DateTime(timezone=True), default=utc_now)
    if not hasattr(cls, 'updated_at'):
        cls.updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    return cls


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)




def init_timestamp_middleware():
    """Initialize timestamp middleware - call this during app startup"""
    TimestampMiddleware.setup_timestamp_listeners()