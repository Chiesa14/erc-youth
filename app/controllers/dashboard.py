from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_, case
from collections import defaultdict
import calendar

from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.family_activity import Activity
from app.models.user import User
from app.schemas.dashboard import (
    ChurchDashboardData, OverallStats, DepartmentData, GenderDistribution,
    MonthlyProgress, AgeDistributionData, DashboardFilters
)
from app.schemas.user import GenderEnum, RoleEnum
from app.schemas.family_activity import ActivityStatusEnum


class DashboardController:
    def __init__(self, db: Session):
        self.db = db

    def get_church_dashboard_data(self, filters: Optional[DashboardFilters] = None) -> ChurchDashboardData:
        """
        Aggregate all dashboard statistics for church pastor view
        """
        if not filters:
            filters = DashboardFilters()

        # Get overall statistics
        overall_stats = self._get_overall_stats(filters)
        
        # Get department (family) performance data
        department_data = self._get_department_data(filters)
        
        # Get gender distribution
        gender_distribution = self._get_gender_distribution()
        
        # Get monthly progress trends
        monthly_progress = self._get_monthly_progress()
        
        # Get age distribution
        age_distribution = self._get_age_distribution()

        return ChurchDashboardData(
            overall_stats=overall_stats,
            department_data=department_data,
            gender_distribution=gender_distribution,
            monthly_progress=monthly_progress,
            age_distribution=age_distribution,
            last_updated=datetime.utcnow()
        )

    def _get_overall_stats(self, filters: DashboardFilters) -> OverallStats:
        """Calculate overall statistics"""
        
        # Total youth (family members)
        total_youth = self.db.query(FamilyMember).count()
        
        # Total families
        total_families = self.db.query(Family).count()
        
        # Gender ratios
        gender_counts = self.db.query(
            FamilyMember.gender,
            func.count(FamilyMember.id).label('count')
        ).group_by(FamilyMember.gender).all()
        
        total_with_gender = sum(count for _, count in gender_counts)
        male_count = next((count for gender, count in gender_counts if gender == GenderEnum.male), 0)
        female_count = next((count for gender, count in gender_counts if gender == GenderEnum.female), 0)
        
        male_ratio = round((male_count / total_with_gender * 100), 1) if total_with_gender > 0 else 0
        female_ratio = round((female_count / total_with_gender * 100), 1) if total_with_gender > 0 else 0
        
        # BCC completion rate
        bcc_participants = self.db.query(FamilyMember).filter(
            FamilyMember.bcc_class_participation.is_(True)
        ).count()
        bcc_completion = round((bcc_participants / total_youth * 100), 1) if total_youth > 0 else 0
        
        # Program implementation (completed activities vs total activities)
        total_activities = self.db.query(Activity).count()
        completed_activities = self.db.query(Activity).filter(
            Activity.status == ActivityStatusEnum.completed
        ).count()
        program_implementation = round((completed_activities / total_activities * 100), 1) if total_activities > 0 else 0
        
        # Active programs (ongoing activities)
        active_programs = self.db.query(Activity).filter(
            Activity.status == ActivityStatusEnum.ongoing
        ).count()
        
        # Pending approvals (planned activities)
        pending_approvals = self.db.query(Activity).filter(
            Activity.status == ActivityStatusEnum.planned
        ).count()

        return OverallStats(
            total_youth=total_youth,
            total_families=total_families,
            male_ratio=male_ratio,
            female_ratio=female_ratio,
            bcc_completion=bcc_completion,
            program_implementation=program_implementation,
            active_programs=active_programs,
            pending_approvals=pending_approvals
        )

    def _get_department_data(self, filters: DashboardFilters) -> List[DepartmentData]:
        """Get performance data by family (department)"""
        
        # Get families with their member counts and statistics
        family_stats = self.db.query(
            Family.name,
            func.count(FamilyMember.id).label('youth_count'),
            func.sum(
                case(
                    (FamilyMember.bcc_class_participation.is_(True), 1),
                    else_=0
                )
            ).label('bcc_participants')
        ).join(FamilyMember, Family.id == FamilyMember.family_id) \
         .group_by(Family.id, Family.name).all()

        # Get activity completion rates by family
        activity_stats = self.db.query(
            Family.name,
            func.count(Activity.id).label('total_activities'),
            func.sum(
                case(
                    (Activity.status == ActivityStatusEnum.completed, 1),
                    else_=0
                )
            ).label('completed_activities')
        ).join(Activity, Family.id == Activity.family_id) \
         .group_by(Family.id, Family.name).all()

        # Create lookup dict for activities
        activity_lookup = {name: (total, completed) for name, total, completed in activity_stats}

        department_data = []
        for family_name, youth_count, bcc_participants in family_stats:
            # Calculate BCC completion rate for this family
            bcc_completion = round((bcc_participants / youth_count * 100), 1) if youth_count > 0 and bcc_participants else 0
            
            # Calculate implementation rate for this family
            total_activities, completed_activities = activity_lookup.get(family_name, (0, 0))
            implementation = round((completed_activities / total_activities * 100), 1) if total_activities > 0 and completed_activities else 0
            
            department_data.append(DepartmentData(
                name=family_name,
                youth=youth_count,
                completion=bcc_completion,
                implementation=implementation
            ))

        return department_data[:10]  # Limit to top 10 families

    def _get_gender_distribution(self) -> List[GenderDistribution]:
        """Get gender distribution data"""
        
        gender_counts = self.db.query(
            FamilyMember.gender,
            func.count(FamilyMember.id).label('count')
        ).group_by(FamilyMember.gender).all()
        
        total = sum(count for _, count in gender_counts)
        
        distribution = []
        colors = {"Male": "#8884d8", "Female": "#82ca9d"}
        
        for gender, count in gender_counts:
            if gender and total > 0:
                percentage = round((count / total * 100), 1)
                distribution.append(GenderDistribution(
                    name=gender.value,
                    value=percentage,
                    color=colors.get(gender.value, "#cccccc")
                ))
        
        return distribution

    def _get_monthly_progress(self) -> List[MonthlyProgress]:
        """Get monthly progress trends for the last 6 months"""
        
        # Get last 6 months
        today = date.today()
        months = []
        for i in range(5, -1, -1):  # Last 6 months including current
            month_date = today.replace(day=1) - timedelta(days=i*30)
            months.append({
                'date': month_date,
                'name': calendar.month_name[month_date.month][:3],
                'year': month_date.year,
                'month': month_date.month
            })

        progress_data = []
        
        for month_info in months:
            # Calculate program implementation for this month
            monthly_activities = self.db.query(Activity).filter(
                and_(
                    extract('year', Activity.date) == month_info['year'],
                    extract('month', Activity.date) == month_info['month']
                )
            ).all()
            
            total_monthly = len(monthly_activities)
            completed_monthly = len([a for a in monthly_activities if a.status == ActivityStatusEnum.completed])
            implementation = round((completed_monthly / total_monthly * 100), 1) if total_monthly > 0 else 0
            
            # For BCC completion, we'll use cumulative data up to this month
            # as BCC completion is more of a cumulative metric
            bcc_participants = self.db.query(FamilyMember).filter(
                and_(
                    FamilyMember.bcc_class_participation.is_(True),
                    FamilyMember.created_at <= datetime(month_info['year'], month_info['month'], 28)
                )
            ).count()
            
            total_members_by_month = self.db.query(FamilyMember).filter(
                FamilyMember.created_at <= datetime(month_info['year'], month_info['month'], 28)
            ).count()
            
            bcc_completion = round((bcc_participants / total_members_by_month * 100), 1) if total_members_by_month > 0 else 0
            
            progress_data.append(MonthlyProgress(
                month=month_info['name'],
                implementation=implementation,
                bcc=bcc_completion
            ))

        return progress_data

    def _get_age_distribution(self) -> List[AgeDistributionData]:
        """Get age distribution of youth members"""
        
        today = date.today()
        
        # Get all members with birth dates
        members = self.db.query(FamilyMember).filter(
            FamilyMember.date_of_birth.isnot(None)
        ).all()
        
        if not members:
            return []
        
        age_groups = {
            "12-14 years": 0,
            "15-17 years": 0,
            "18+ years": 0
        }
        
        for member in members:
            age = today.year - member.date_of_birth.year
            if (today.month, today.day) < (member.date_of_birth.month, member.date_of_birth.day):
                age -= 1
                
            if 12 <= age <= 14:
                age_groups["12-14 years"] += 1
            elif 15 <= age <= 17:
                age_groups["15-17 years"] += 1
            elif age >= 18:
                age_groups["18+ years"] += 1

        total = len(members)
        
        return [
            AgeDistributionData(
                age_group=group,
                percentage=round((count / total * 100), 1) if total > 0 else 0
            )
            for group, count in age_groups.items()
        ]