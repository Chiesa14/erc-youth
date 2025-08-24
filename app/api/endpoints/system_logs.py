from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.system_log import SystemLog
from app.schemas.system_log import SystemLogResponse, SystemLogFilter
from sqlalchemy import and_, or_, desc

router = APIRouter()


@router.get("/", response_model=List[SystemLogResponse])
async def get_system_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[int] = Query(None),
    family_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get system logs with filtering and pagination.
    Only admin users can access all logs, regular users can only see their own logs.
    """
    
    # Build query
    query = db.query(SystemLog)
    
    # Apply user restrictions
    if current_user.role.value != "admin":
        # Regular users can only see their own logs
        query = query.filter(SystemLog.user_id == current_user.id)
    
    # Apply filters
    if user_id:
        query = query.filter(SystemLog.user_id == user_id)
    
    if family_id:
        query = query.filter(SystemLog.family_id == family_id)
    
    if action:
        query = query.filter(SystemLog.action.ilike(f"%{action}%"))
    
    if table_name:
        query = query.filter(SystemLog.table_name.ilike(f"%{table_name}%"))
    
    if start_date:
        query = query.filter(SystemLog.created_at >= start_date)
    
    if end_date:
        query = query.filter(SystemLog.created_at <= end_date)
    
    if search:
        search_filter = or_(
            SystemLog.description.ilike(f"%{search}%"),
            SystemLog.user_name.ilike(f"%{search}%"),
            SystemLog.family_name.ilike(f"%{search}%"),
            SystemLog.action.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Order by creation date (newest first)
    query = query.order_by(desc(SystemLog.created_at))
    
    # Apply pagination
    total = query.count()
    logs = query.offset(skip).limit(limit).all()
    
    return logs


@router.get("/summary", response_model=dict)
async def get_system_logs_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365)
):
    """
    Get summary statistics of system logs for the specified number of days.
    """
    
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Only admin users can access log summaries")
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get logs in date range
    logs = db.query(SystemLog).filter(
        and_(
            SystemLog.created_at >= start_date,
            SystemLog.created_at <= end_date
        )
    ).all()
    
    # Calculate statistics
    total_actions = len(logs)
    actions_by_type = {}
    actions_by_user = {}
    actions_by_family = {}
    actions_by_table = {}
    
    for log in logs:
        # Count by action type
        actions_by_type[log.action] = actions_by_type.get(log.action, 0) + 1
        
        # Count by user
        actions_by_user[log.user_name] = actions_by_user.get(log.user_name, 0) + 1
        
        # Count by family
        if log.family_name:
            actions_by_family[log.family_name] = actions_by_family.get(log.family_name, 0) + 1
        
        # Count by table
        if log.table_name:
            actions_by_table[log.table_name] = actions_by_table.get(log.table_name, 0) + 1
    
    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_actions": total_actions,
        "actions_by_type": actions_by_type,
        "top_users": dict(sorted(actions_by_user.items(), key=lambda x: x[1], reverse=True)[:10]),
        "top_families": dict(sorted(actions_by_family.items(), key=lambda x: x[1], reverse=True)[:10]),
        "top_tables": dict(sorted(actions_by_table.items(), key=lambda x: x[1], reverse=True)[:10])
    }


@router.get("/user/{user_id}", response_model=List[SystemLogResponse])
async def get_user_logs(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get logs for a specific user.
    Users can only see their own logs, admins can see any user's logs.
    """
    
    if current_user.id != user_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="You can only view your own logs")
    
    logs = db.query(SystemLog).filter(
        SystemLog.user_id == user_id
    ).order_by(desc(SystemLog.created_at)).offset(skip).limit(limit).all()
    
    return logs


@router.get("/family/{family_id}", response_model=List[SystemLogResponse])
async def get_family_logs(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get logs for a specific family.
    Users can only see logs for their own family, admins can see any family's logs.
    """
    
    if current_user.family_id != family_id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="You can only view logs for your own family")
    
    logs = db.query(SystemLog).filter(
        SystemLog.family_id == family_id
    ).order_by(desc(SystemLog.created_at)).offset(skip).limit(limit).all()
    
    return logs


@router.get("/recent", response_model=List[SystemLogResponse])
async def get_recent_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    hours: int = Query(24, ge=1, le=168)  # Max 1 week
):
    """
    Get recent logs from the last specified hours.
    """
    
    # Calculate time range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)
    
    # Build query
    query = db.query(SystemLog).filter(
        and_(
            SystemLog.created_at >= start_date,
            SystemLog.created_at <= end_date
        )
    )
    
    # Apply user restrictions
    if current_user.role.value != "admin":
        query = query.filter(SystemLog.user_id == current_user.id)
    
    # Get recent logs
    logs = query.order_by(desc(SystemLog.created_at)).limit(100).all()
    
    return logs
