"""
API routes for church performance analytics.
Provides comprehensive analytics data for the frontend dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime, timedelta

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.user import RoleEnum
from app.services.analytics_service import AnalyticsService
from app.models.family_member import FamilyMember
from app.models.family import Family
from app.schemas.analytics import CommissionDistribution, CommissionCount
from app.schemas.analytics import (
    ChurchPerformanceAnalytics,
    AnalyticsFilters,
    PerformanceInsights,
    FamilyEngagementDetail,
    ActivitySummary
)

router = APIRouter(tags=["Church Analytics"])


@router.get("/commissions", response_model=CommissionDistribution)
def get_commission_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get commission distribution overall and by family category.

    Only accessible to church pastor and admin.
    """

    if current_user.role not in {RoleEnum.church_pastor, RoleEnum.admin}:
        raise HTTPException(status_code=403, detail="Access denied")

    rows = (
        db.query(
            Family.category.label("category"),
            FamilyMember.commission.label("commission"),
            func.count(FamilyMember.id).label("count"),
        )
        .join(Family, Family.id == FamilyMember.family_id)
        .filter(FamilyMember.commission.isnot(None))
        .filter(FamilyMember.commission != "")
        .group_by(Family.category, FamilyMember.commission)
        .all()
    )

    by_category = {}
    overall_counts = {}
    for category, commission, count in rows:
        overall_counts[commission] = overall_counts.get(commission, 0) + int(count)
        by_category.setdefault(category, {})
        by_category[category][commission] = by_category[category].get(commission, 0) + int(count)

    overall = [
        CommissionCount(commission=c, count=cnt)
        for c, cnt in sorted(overall_counts.items(), key=lambda x: (-x[1], x[0]))
    ]

    by_category_out = {
        cat: [
            CommissionCount(commission=c, count=cnt)
            for c, cnt in sorted(commissions.items(), key=lambda x: (-x[1], x[0]))
        ]
        for cat, commissions in by_category.items()
    }

    return CommissionDistribution(overall=overall, by_category=by_category_out)


@router.get("/performance", response_model=ChurchPerformanceAnalytics)
def get_church_performance_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    family_ids: Optional[str] = Query(None, description="Comma-separated family IDs to filter")
):
    """
    Get comprehensive church performance analytics including:
    - Overall performance metrics
    - Family-specific performance data
    - Program statistics
    """
    
    # Parse dates
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    # Parse family IDs
    family_id_list = None
    if family_ids:
        try:
            family_id_list = [int(fid.strip()) for fid in family_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid family_ids format")
    
    # For non-admin users, restrict to their family only
    if current_user.role != RoleEnum.church_pastor and current_user.family_id:
        family_id_list = [current_user.family_id]
    elif current_user.role != RoleEnum.church_pastor and not current_user.family_id:
        raise HTTPException(status_code=403, detail="Access denied: No family association")
    
    # Get analytics data
    service = AnalyticsService(db)
    analytics = service.get_church_performance_analytics(
        start_date=start_dt,
        end_date=end_dt,
        family_ids=family_id_list
    )
    
    return analytics


@router.get("/performance/families", response_model=List[FamilyEngagementDetail])
def get_family_engagement_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    limit: int = Query(50, description="Maximum number of families to return")
):
    """
    Get detailed family engagement metrics
    """
    
    # Only admins can access all families, others see their own family
    if current_user.role != RoleEnum.church_pastor:
        if not current_user.family_id:
            raise HTTPException(status_code=403, detail="Access denied: No family association")
    
    # Parse dates
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    family_ids = [current_user.family_id] if current_user.role != RoleEnum.church_pastor else None
    
    service = AnalyticsService(db)
    analytics = service.get_church_performance_analytics(
        start_date=start_dt,
        end_date=end_dt,
        family_ids=family_ids
    )
    
    # Convert family metrics to engagement details
    engagement_details = []
    for family_metric in analytics.family_metrics[:limit]:
        engagement_details.append(FamilyEngagementDetail(
            family_id=family_metric.family_id,
            family_name=family_metric.family_name,
            total_members=5,  # This would need to be calculated from FamilyMember model
            active_members=4,  # This would need to be calculated based on recent activity
            recent_activities=family_metric.activities_completed,
            last_activity_date=family_metric.last_active,
            engagement_score=family_metric.engagement,
            participation_trend=family_metric.trend
        ))
    
    return engagement_details


@router.get("/performance/programs")
def get_program_performance_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    program_type: Optional[str] = Query(None, description="Filter by program type: bcc, fhe, service, youth")
):
    """
    Get detailed program performance metrics
    """
    
    # Only admins can access system-wide program statistics
    if current_user.role != RoleEnum.church_pastor:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Parse dates
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    service = AnalyticsService(db)
    analytics = service.get_church_performance_analytics(
        start_date=start_dt,
        end_date=end_dt
    )
    
    program_stats = analytics.program_stats
    
    # Filter by program type if specified
    if program_type:
        program_map = {
            'bcc': program_stats.bcc_program,
            'fhe': program_stats.fhe_program,
            'service': program_stats.service_projects,
            'youth': program_stats.youth_activities
        }
        
        if program_type not in program_map:
            raise HTTPException(status_code=400, detail="Invalid program_type. Use: bcc, fhe, service, youth")
        
        return {program_type: program_map[program_type]}
    
    return {
        'bcc_program': program_stats.bcc_program,
        'fhe_program': program_stats.fhe_program,
        'service_projects': program_stats.service_projects,
        'youth_activities': program_stats.youth_activities
    }


@router.get("/insights", response_model=PerformanceInsights)
def get_performance_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format")
):
    """
    Get performance insights and recommendations
    """
    
    # Only admins can access insights
    if current_user.role != RoleEnum.church_pastor:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Parse dates
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    service = AnalyticsService(db)
    insights = service.get_performance_insights(
        start_date=start_dt,
        end_date=end_dt
    )
    
    return insights


@router.get("/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    days: int = Query(30, description="Number of days to look back")
):
    """
    Get a quick analytics summary for the dashboard
    """
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    family_ids = [current_user.family_id] if current_user.role != RoleEnum.church_pastor and current_user.family_id else None
    
    service = AnalyticsService(db)
    analytics = service.get_church_performance_analytics(
        start_date=start_date,
        end_date=end_date,
        family_ids=family_ids
    )
    
    # Create summary
    summary = {
        "period_days": days,
        "total_families": len(analytics.family_metrics),
        "overall_metrics": {
            "participation_rate": analytics.overall.participation_rate,
            "program_completion": analytics.overall.program_completion,
            "family_engagement": analytics.overall.family_engagement,
            "youth_retention": analytics.overall.youth_retention,
            "trend": analytics.overall.trend
        },
        "top_performing_families": [
            {
                "name": f.family_name,
                "participation": f.participation,
                "trend": f.trend
            }
            for f in analytics.family_metrics[:5]
        ],
        "program_performance": {
            "bcc_program": analytics.program_stats.bcc_program.average_score,
            "fhe_program": analytics.program_stats.fhe_program.average_score,
            "service_projects": analytics.program_stats.service_projects.average_score,
            "youth_activities": analytics.program_stats.youth_activities.average_score
        }
    }
    
    return summary


@router.get("/export")
def export_analytics_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    format: str = Query("json", description="Export format: json or csv")
):
    """
    Export analytics data for reporting
    """
    
    # Only admins can export data
    if current_user.role != RoleEnum.church_pastor:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Parse dates
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    service = AnalyticsService(db)
    analytics = service.get_church_performance_analytics(
        start_date=start_dt,
        end_date=end_dt
    )
    
    if format.lower() == "json":
        return {
            "export_date": datetime.now().isoformat(),
            "period": {
                "start_date": start_dt.isoformat() if start_dt else None,
                "end_date": end_dt.isoformat() if end_dt else None
            },
            "data": analytics.dict()
        }
    else:
        # For CSV format, you would implement CSV conversion here
        raise HTTPException(status_code=400, detail="CSV export not yet implemented")