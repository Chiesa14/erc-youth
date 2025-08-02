"""
API routes for timestamp analytics and advanced timestamp-based queries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.timestamp_service import TimestampQueryService
from app.utils.timestamps import from_iso_format
from app.models.user import User as UserModel
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.family_activity import Activity
from app.models.announcement import Announcement
from app.models.shared_document import SharedDocument
from app.models.family_document import FamilyDocument

router = APIRouter(tags=["Timestamp Analytics"])

# Model mapping for dynamic queries
MODEL_MAP = {
    'users': UserModel,
    'families': Family,
    'family_members': FamilyMember,
    'activities': Activity,
    'announcements': Announcement,
    'shared_documents': SharedDocument,
    'family_documents': FamilyDocument
}


@router.get("/recent/{model_name}")
def get_recent_records(
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    hours: int = Query(24, description="Number of hours to look back"),
    limit: int = Query(50, description="Maximum number of records to return")
):
    """Get recently created or updated records for a specific model"""
    
    if model_name not in MODEL_MAP:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model name. Available models: {list(MODEL_MAP.keys())}"
        )
    
    # Only admins can access all models, others are restricted
    if current_user.role != "admin":
        # Non-admin users can only access their family's data
        if model_name in ['families', 'family_members', 'activities'] and not current_user.family_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    service = TimestampQueryService(db)
    model_class = MODEL_MAP[model_name]
    
    records = service.get_recent_records(model_class, hours, limit)
    
    # Filter by family for non-admin users
    if current_user.role != "admin" and current_user.family_id:
        if hasattr(model_class, 'family_id'):
            records = [r for r in records if getattr(r, 'family_id', None) == current_user.family_id]
        elif model_name == 'users':
            records = [r for r in records if r.family_id == current_user.family_id]
    
    return {
        "model": model_name,
        "hours_back": hours,
        "count": len(records),
        "records": records
    }


@router.get("/timeline")
def get_activity_timeline(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(None, description="Start date in ISO 8601 format"),
    end_date: Optional[str] = Query(None, description="End date in ISO 8601 format"),
    limit: int = Query(100, description="Maximum number of records per model")
):
    """Get a timeline of activities across all models"""
    
    service = TimestampQueryService(db)
    
    # Parse dates
    start_dt = from_iso_format(start_date) if start_date else None
    end_dt = from_iso_format(end_date) if end_date else None
    
    # For non-admin users, restrict to their family
    family_id = None if current_user.role == "admin" else current_user.family_id
    
    timeline = service.get_activity_timeline(family_id, start_dt, end_dt, limit)
    
    return {
        "family_id": family_id,
        "start_date": start_date,
        "end_date": end_date,
        "timeline": timeline
    }


@router.get("/statistics")
def get_timestamp_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive timestamp statistics"""
    
    # Only admins can access system-wide statistics
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = TimestampQueryService(db)
    stats = service.get_timestamp_statistics()
    
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "statistics": stats
    }


@router.get("/history/{model_name}/{record_id}")
def get_modification_history(
    model_name: str,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    include_related: bool = Query(False, description="Include related record information")
):
    """Get modification history for a specific record"""
    
    if model_name not in MODEL_MAP:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model name. Available models: {list(MODEL_MAP.keys())}"
        )
    
    model_class = MODEL_MAP[model_name]
    
    # Check if record exists and user has access
    record = db.query(model_class).filter(model_class.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Access control for non-admin users
    if current_user.role != "admin":
        if hasattr(record, 'family_id') and record.family_id != current_user.family_id:
            raise HTTPException(status_code=403, detail="Access denied")
        elif model_name == 'users' and record.family_id != current_user.family_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    service = TimestampQueryService(db)
    history = service.get_modification_history(model_class, record_id, include_related)
    
    return history


@router.get("/stale/{model_name}")
def get_stale_records(
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days_threshold: int = Query(30, description="Number of days to consider a record stale")
):
    """Get records that haven't been updated in a specified number of days"""
    
    if model_name not in MODEL_MAP:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model name. Available models: {list(MODEL_MAP.keys())}"
        )
    
    # Only admins can access stale record analysis
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = TimestampQueryService(db)
    model_class = MODEL_MAP[model_name]
    
    stale_records = service.find_stale_records(model_class, days_threshold)
    
    return {
        "model": model_name,
        "days_threshold": days_threshold,
        "count": len(stale_records),
        "records": stale_records
    }


@router.get("/activity-patterns/{model_name}")
def get_activity_patterns(
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days: int = Query(30, description="Number of days to analyze")
):
    """Get activity patterns showing the most active periods"""
    
    if model_name not in MODEL_MAP:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model name. Available models: {list(MODEL_MAP.keys())}"
        )
    
    # Only admins can access activity pattern analysis
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    service = TimestampQueryService(db)
    model_class = MODEL_MAP[model_name]
    
    patterns = service.get_most_active_periods(model_class, days)
    
    return {
        "model": model_name,
        "analysis_period_days": days,
        "hourly_activity": patterns,
        "peak_hours": list(patterns.keys())[:5] if patterns else []
    }


@router.get("/health-check")
def timestamp_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Check the health of timestamp functionality across all models"""
    
    # Only admins can access health check
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    health_status = {
        "timestamp_middleware_active": True,
        "models_with_timestamps": [],
        "models_missing_timestamps": [],
        "recent_activity": {}
    }
    
    # Check each model for timestamp fields
    for model_name, model_class in MODEL_MAP.items():
        has_created_at = hasattr(model_class, 'created_at')
        has_updated_at = hasattr(model_class, 'updated_at')
        
        if has_created_at and has_updated_at:
            health_status["models_with_timestamps"].append(model_name)
            
            # Check for recent activity
            recent_count = db.query(model_class).filter(
                model_class.created_at >= datetime.utcnow() - timedelta(hours=24)
            ).count()
            health_status["recent_activity"][model_name] = recent_count
        else:
            health_status["models_missing_timestamps"].append({
                "model": model_name,
                "has_created_at": has_created_at,
                "has_updated_at": has_updated_at
            })
    
    health_status["overall_health"] = len(health_status["models_missing_timestamps"]) == 0
    
    return health_status