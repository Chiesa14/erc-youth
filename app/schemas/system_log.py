from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class SystemLogBase(BaseModel):
    """Base schema for system logs"""
    user_id: int
    user_name: str
    family_id: Optional[int] = None
    family_name: Optional[str] = None
    family_category: Optional[str] = None
    action: str
    description: str
    table_name: Optional[str] = None
    record_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class SystemLogResponse(SystemLogBase):
    """Schema for system log responses"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class SystemLogFilter(BaseModel):
    """Schema for filtering system logs"""
    user_id: Optional[int] = None
    family_id: Optional[int] = None
    action: Optional[str] = None
    table_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None
    skip: int = 0
    limit: int = 100


class SystemLogSummary(BaseModel):
    """Schema for system log summary statistics"""
    period_days: int
    start_date: str
    end_date: str
    total_actions: int
    actions_by_type: Dict[str, int]
    top_users: Dict[str, int]
    top_families: Dict[str, int]
    top_tables: Dict[str, int]


class SystemLogCreate(BaseModel):
    """Schema for creating system logs (internal use)"""
    user_id: int
    user_name: str
    family_id: Optional[int] = None
    family_name: Optional[str] = None
    family_category: Optional[str] = None
    action: str
    description: str
    table_name: Optional[str] = None
    record_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
