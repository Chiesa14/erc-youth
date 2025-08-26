from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import logging
from datetime import datetime

from app.controllers.dashboard import DashboardController
from app.schemas.dashboard import (
    ChurchDashboardData, DashboardFilters, AdminDashboardData,
    ParentDashboardData, YouthDashboardData
)
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


@router.get("/admin-overview", response_model=AdminDashboardData)
def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get admin dashboard with user statistics and recent activities.
    
    Includes:
    - User statistics (total, new this month, changes)
    - Recent user activities
    - System overview metrics
    
    Only accessible to administrators.
    """
    logger.info(f"Admin dashboard access requested by user {current_user.id} with role {current_user.role}")
    
    # Restrict access to admins only
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only administrators can view this dashboard."
        )
    
    try:
        dashboard_controller = DashboardController(db)
        dashboard_data = dashboard_controller.get_admin_dashboard_data()
        
        logger.info(f"Admin dashboard data successfully retrieved for user {current_user.id}")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error retrieving admin dashboard data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve admin dashboard data: {str(e)}"
        )


@router.get("/parent-overview", response_model=ParentDashboardData)
def get_parent_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get parent/family dashboard with family-specific statistics.
    
    Includes:
    - Family member statistics
    - Age distribution within family
    - Activity trends and engagement
    - BCC completion status
    
    Accessible to family parents (pere, mere).
    """
    logger.info(f"Parent dashboard access requested by user {current_user.id} with role {current_user.role}")
    
    # Restrict access to family parents
    if current_user.role not in {RoleEnum.pere, RoleEnum.mere}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only family parents can view this dashboard."
        )
    
    # Check if user has a family_id
    if not current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not associated with a family."
        )
    
    try:
        dashboard_controller = DashboardController(db)
        dashboard_data = dashboard_controller.get_parent_dashboard_data(current_user.family_id)
        
        logger.info(f"Parent dashboard data successfully retrieved for user {current_user.id}, family {current_user.family_id}")
        return dashboard_data
        
    except ValueError as ve:
        logger.error(f"Family not found: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error retrieving parent dashboard data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve parent dashboard data: {str(e)}"
        )


@router.get("/youth-overview", response_model=YouthDashboardData)
def get_youth_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get youth dashboard with community engagement and quick actions.
    
    Includes:
    - Quick action buttons with notification counts
    - Community statistics and engagement metrics
    - Recent announcements and updates
    - Youth-focused navigation
    
    Accessible to youth and family members.
    """
    logger.info(f"Youth dashboard access requested by user {current_user.id} with role {current_user.role}")
    
    # Allow access to youth and family members
    if current_user.role not in {RoleEnum.youth, RoleEnum.pere, RoleEnum.mere}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only youth and family members can view this dashboard."
        )
    
    try:
        dashboard_controller = DashboardController(db)
        dashboard_data = dashboard_controller.get_youth_dashboard_data()
        
        logger.info(f"Youth dashboard data successfully retrieved for user {current_user.id}")
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error retrieving youth dashboard data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve youth dashboard data: {str(e)}"
        )


@router.get("/family/{family_id}/stats", response_model=ParentDashboardData)
def get_family_stats(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get family statistics for a specific family.
    This endpoint matches the frontend API call pattern: /families/{family_id}/stats
    
    Accessible to family members and admins.
    """
    logger.info(f"Family stats access requested for family {family_id} by user {current_user.id}")
    
    # Check permissions - either family member or admin
    if current_user.role == RoleEnum.admin:
        # Admin can access any family
        pass
    elif current_user.family_id == family_id and current_user.role in {RoleEnum.pere, RoleEnum.mere, RoleEnum.youth}:
        # Family member can access their own family
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own family's statistics."
        )
    
    try:
        dashboard_controller = DashboardController(db)
        dashboard_data = dashboard_controller.get_parent_dashboard_data(family_id)
        
        logger.info(f"Family stats successfully retrieved for family {family_id}")
        return dashboard_data
        
    except ValueError as ve:
        logger.error(f"Family not found: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error retrieving family stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve family statistics: {str(e)}"
        )