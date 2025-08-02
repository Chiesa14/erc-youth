"""
Timestamp utilities for handling createdAt and updatedAt fields
with proper timezone support and ISO 8601 formatting.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Session
from pydantic import BaseModel


def utc_now() -> datetime:
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)


def to_iso_format(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO 8601 format string"""
    if dt is None:
        return None
    
    # Ensure timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.isoformat()


def from_iso_format(iso_string: Optional[str]) -> Optional[datetime]:
    """Convert ISO 8601 format string to datetime"""
    if not iso_string:
        return None
    
    try:
        return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    except ValueError:
        return None


def add_timestamps_to_dict(data: Dict[str, Any], created_at: Optional[datetime] = None, 
                          updated_at: Optional[datetime] = None) -> Dict[str, Any]:
    """Add timestamp fields to a dictionary with ISO formatting"""
    result = data.copy()
    result['created_at'] = to_iso_format(created_at)
    result['updated_at'] = to_iso_format(updated_at)
    return result


class TimestampMixin:
    """Mixin class to add timestamp functionality to Pydantic models"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


def parse_timestamp_filters(
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None
) -> Dict[str, Optional[datetime]]:
    """Parse timestamp filter parameters from ISO strings to datetime objects"""
    return {
        'created_after': from_iso_format(created_after),
        'created_before': from_iso_format(created_before),
        'updated_after': from_iso_format(updated_after),
        'updated_before': from_iso_format(updated_before)
    }


def apply_timestamp_filters(query, model_class, filters: Dict[str, Optional[datetime]]):
    """Apply timestamp filters to a SQLAlchemy query"""
    if filters.get('created_after'):
        query = query.filter(model_class.created_at >= filters['created_after'])
    
    if filters.get('created_before'):
        query = query.filter(model_class.created_at <= filters['created_before'])
    
    if filters.get('updated_after'):
        query = query.filter(model_class.updated_at >= filters['updated_after'])
    
    if filters.get('updated_before'):
        query = query.filter(model_class.updated_at <= filters['updated_before'])
    
    return query


def apply_timestamp_sorting(query, model_class, sort_by: Optional[str] = None, 
                           sort_order: Optional[str] = "desc"):
    """Apply timestamp-based sorting to a SQLAlchemy query"""
    if not sort_by:
        return query
    
    sort_column = None
    if sort_by == "created_at":
        sort_column = model_class.created_at
    elif sort_by == "updated_at":
        sort_column = model_class.updated_at
    
    if sort_column is not None:
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
    
    return query


class TimestampQueryParams(BaseModel):
    """Common query parameters for timestamp filtering and sorting"""
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    updated_after: Optional[str] = None
    updated_before: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "desc"
    
    class Config:
        json_schema_extra = {
            "example": {
                "created_after": "2024-01-01T00:00:00Z",
                "created_before": "2024-12-31T23:59:59Z",
                "updated_after": "2024-06-01T00:00:00Z",
                "updated_before": "2024-06-30T23:59:59Z",
                "sort_by": "created_at",
                "sort_order": "desc"
            }
        }