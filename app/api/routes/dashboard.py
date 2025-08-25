from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import logging
from datetime import datetime

from app.controllers.dashboard import DashboardController
from app.schemas.dashboard import ChurchDashboardData, DashboardFilters
from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.user import RoleEnum

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])


@router.get("/church-overview", response_model=ChurchDashboardData)
def get_church_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    department_filter: Optional[str] = Query("all", description="Filter departments: all, active, pending"),
    date_range: Optional[str] = Query("6months", description="Date range for trends: 1month, 3months, 6months, 1year"),
):
    """
    Get comprehensive church dashboard statistics for pastor overview.
    
    Includes:
    - Overall stats (total youth, families, completion rates)
    - Department/Family performance data
    - Gender and age distributions
    - Monthly progress trends
    
    Only accessible to church pastors and admins.
    """
    logger.info(f"Dashboard access requested by user {current_user.id} with role {current_user.role}")
    
    # Restrict access to church pastors and admins
    if current_user.role not in {RoleEnum.admin, RoleEnum.church_pastor}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only church pastors and administrators can view this dashboard."
        )
    
    try:
        # Create filters object
        filters = DashboardFilters(
            department_filter=department_filter,
            date_range=date_range
        )
        
        # Get dashboard data using controller
        dashboard_controller = DashboardController(db)
        dashboard_data = dashboard_controller.get_church_dashboard_data(filters)
        
        logger.info(f"Dashboard data successfully retrieved for user {current_user.id}")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard data: {str(e)}"
        )


@router.get("/church-stats-summary")
def get_church_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a quick summary of key church statistics.
    Lighter endpoint for quick status checks.
    """
    # Allow access to more roles for quick stats
    if current_user.role not in {RoleEnum.admin, RoleEnum.church_pastor, RoleEnum.pere, RoleEnum.mere}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Insufficient permissions to view church statistics."
        )
    
    try:
        dashboard_controller = DashboardController(db)
        filters = DashboardFilters()  # Default filters
        
        # Get only overall stats for quick summary
        overall_stats = dashboard_controller._get_overall_stats(filters)
        
        return {
            "total_youth": overall_stats.total_youth,
            "total_families": overall_stats.total_families,
            "bcc_completion_rate": overall_stats.bcc_completion,
            "active_programs": overall_stats.active_programs,
            "pending_approvals": overall_stats.pending_approvals,
            "last_updated": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error retrieving stats summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics summary: {str(e)}"
        )