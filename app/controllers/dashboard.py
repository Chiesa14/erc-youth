from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_, case
from collections import defaultdict
import calendar

from app.models.family import Family
from app.models.family_document import FamilyDocument
from app.models.family_member import FamilyMember
from app.models.family_activity import Activity
from app.models.user import User
from app.models.system_log import SystemLog
from app.models.announcement import Announcement
from app.models.feedback import Feedback
from app.schemas.dashboard import (
    ChurchDashboardData, OverallStats, DepartmentData, GenderDistribution,
    MonthlyProgress, AgeDistributionData, DashboardFilters,
    AdminDashboardData, AdminStats, RecentActivity,
    ParentDashboardData, FamilyStats, FamilyAgeDistribution, MonthlyTrend,
    YouthDashboardData, QuickAction, CommunityStat, YouthUpdate
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
            last_updated=datetime.now(timezone.utc)
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

    def get_admin_dashboard_data(self) -> AdminDashboardData:
        """
        Get dashboard data for admin users
        """
        # Get current date info for calculations
        now = datetime.now(timezone.utc)
        current_year = now.year
        current_month = now.month
        
        # Previous month calculation
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year

        # Get user statistics
        total_users = self.db.query(User).count()
        
        # Users created this month
        new_users_this_month = self.db.query(User).filter(
            and_(
                extract('year', User.created_at) == current_year,
                extract('month', User.created_at) == current_month
            )
        ).count()
        
        # Users created last month
        new_users_last_month = self.db.query(User).filter(
            and_(
                extract('year', User.created_at) == prev_year,
                extract('month', User.created_at) == prev_month
            )
        ).count()
        
        # Calculate changes
        total_users_last_month = total_users - new_users_this_month
        
        def calc_percent_change(current: int, previous: int) -> str:
            if previous == 0:
                return "+100%" if current > 0 else "0%"
            change = ((current - previous) / previous) * 100
            return f"+{change:.0f}%" if change >= 0 else f"{change:.0f}%"
        
        total_users_change = calc_percent_change(total_users, total_users_last_month)
        new_users_change = calc_percent_change(new_users_this_month, new_users_last_month)
        
        # Get actual reports submitted (feedback submissions)
        reports_submitted = self.db.query(FamilyDocument).count()
        active_families = self.db.query(Family).count()
        
        # Create admin stats
        admin_stats = AdminStats(
            total_users=total_users,
            new_users_this_month=new_users_this_month,
            new_users_last_month=new_users_last_month,
            reports_submitted=reports_submitted,
            active_families=active_families,
            total_users_change=total_users_change,
            new_users_change=new_users_change
        )
        
        # Get recent activities from system logs
        recent_logs = self.db.query(SystemLog).order_by(
            SystemLog.created_at.desc()
        ).limit(10).all()
        
        recent_activities = []
        for log in recent_logs:
            # Calculate time difference (ensure timezone-aware datetimes)
            now_utc = datetime.now(timezone.utc)
            log_created_at = log.created_at.replace(tzinfo=timezone.utc) if log.created_at.tzinfo is None else log.created_at
            time_diff = now_utc - log_created_at
            if time_diff.days > 0:
                time_str = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif time_diff.seconds >= 60:
                minutes = time_diff.seconds // 60
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                time_str = "Just now"
            
            # Determine activity type based on action and table
            activity_type = "log"
            if log.table_name in ["feedback","announcements"]:
                activity_type = "announcements"
            elif log.table_name == "family_members":
                activity_type = "registration"
            elif log.table_name in ["families", "user"]:
                activity_type = "update"
            elif log.table_name in ["shared_documents", "Documents"]:
                activity_type = "documents"
            elif log.action == "LOGIN":
                activity_type = "access"
            
            recent_activities.append(RecentActivity(
                user=log.user_name,
                action=log.action,
                time=time_str,
                type=activity_type,
                user_id=log.user_id,
                family_id=log.family_id,
                family_name=log.family_name,
                table_name=log.table_name,
                record_id=log.record_id,
                details=log.description
            ))
        
        return AdminDashboardData(
            stats=admin_stats,
            recent_activities=recent_activities,
            last_updated=datetime.now(timezone.utc)
        )

    def get_parent_dashboard_data(self, family_id: int) -> ParentDashboardData:
        """
        Get dashboard data for parent/family users
        """
        # Get family and its members
        family = self.db.query(Family).filter(Family.id == family_id).first()
        if not family:
            raise ValueError(f"Family with id {family_id} not found")
        
        family_members = self.db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id
        ).all()
        
        total_members = len(family_members)
        
        # Calculate monthly members (new members this month)
        now = datetime.now(timezone.utc)
        monthly_members = len([
            member for member in family_members
            if member.created_at and
            member.created_at.year == now.year and
            member.created_at.month == now.month
        ])
        
        # BCC graduates
        bcc_graduate = len([
            member for member in family_members
            if member.bcc_class_participation
        ])
        
        # Get family activities
        family_activities = self.db.query(Activity).filter(
            Activity.family_id == family_id
        ).all()
        
        active_events = len([
            activity for activity in family_activities
            if activity.status == ActivityStatusEnum.ongoing
        ])
        
        # Weekly events (this week)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        weekly_events = len([
            activity for activity in family_activities
            if activity.date and week_start <= activity.date.date() <= week_end
        ])
        
        # Calculate engagement based on completed activities
        engagement = len([
            activity for activity in family_activities
            if activity.status == ActivityStatusEnum.completed
        ])
        
        # Age distribution
        age_distribution = FamilyAgeDistribution(
            zero_to_twelve=0,
            thirteen_to_eighteen=0,
            nineteen_to_twenty_five=0,
            thirty_five_plus=0
        )
        
        today = date.today()
        for member in family_members:
            if member.date_of_birth:
                age = today.year - member.date_of_birth.year
                if (today.month, today.day) < (member.date_of_birth.month, member.date_of_birth.day):
                    age -= 1
                    
                if 0 <= age <= 12:
                    age_distribution.zero_to_twelve += 1
                elif 13 <= age <= 18:
                    age_distribution.thirteen_to_eighteen += 1
                elif 19 <= age <= 25:
                    age_distribution.nineteen_to_twenty_five += 1
                elif age >= 35:
                    age_distribution.thirty_five_plus += 1
        
        # Activity trends (last 6 months)
        activity_trends = {}
        for i in range(6):
            month_date = today.replace(day=1) - timedelta(days=i*30)
            month_key = month_date.strftime('%Y-%m')
            
            # Count spiritual and social activities for this month
            month_activities = [
                activity for activity in family_activities
                if activity.date and
                activity.date.year == month_date.year and
                activity.date.month == month_date.month
            ]
            
            # Categorize activities based on description keywords
            spiritual_keywords = ['prayer', 'bible', 'worship', 'service', 'devotion', 'spiritual', 'church', 'scripture']
            social_keywords = ['social', 'community', 'fellowship', 'outing', 'meeting', 'gathering', 'event', 'celebration']
            
            spiritual_count = 0
            social_count = 0
            
            for activity in month_activities:
                description_lower = activity.description.lower()
                if any(keyword in description_lower for keyword in spiritual_keywords):
                    spiritual_count += 1
                elif any(keyword in description_lower for keyword in social_keywords):
                    social_count += 1
                else:
                    # Default categorization based on activity type or other logic
                    social_count += 1  # Default to social if unclear
            
            activity_trends[month_key] = MonthlyTrend(
                spiritual=spiritual_count,
                social=social_count
            )
        
        family_stats = FamilyStats(
            total_members=total_members,
            monthly_members=monthly_members,
            bcc_graduate=bcc_graduate,
            active_events=active_events,
            weekly_events=weekly_events,
            engagement=engagement,
            age_distribution=age_distribution,
            activity_trends=activity_trends
        )
        
        return ParentDashboardData(
            family_stats=family_stats,
            last_updated=datetime.now(timezone.utc)
        )

    def get_youth_dashboard_data(self) -> YouthDashboardData:
        """
        Get dashboard data for youth users
        """
        # Get real counts for quick actions
        now = datetime.now(timezone.utc)
        
        # Count recent announcements (last 7 days)
        recent_announcements = self.db.query(Announcement).filter(
            Announcement.created_at >= now - timedelta(days=7)
        ).count()
        
        # Count pending feedback (can be interpreted as feedback opportunities)
        pending_feedback = self.db.query(Feedback).filter(
            Feedback.status == 'new'
        ).count()
        
        # Count upcoming events (activities in next 30 days)
        upcoming_events = self.db.query(Activity).filter(
            and_(
                Activity.date >= now.date(),
                Activity.date <= (now + timedelta(days=30)).date(),
                Activity.status.in_(['planned', 'ongoing'])
            )
        ).count()
        
        # Count available documents (shared documents)
        try:
            from app.models.shared_document import SharedDocument
            available_documents = self.db.query(SharedDocument).count()
        except ImportError:
            # Fallback if SharedDocument model is not available
            available_documents = 0
        
        quick_actions = [
            QuickAction(
                title="Announcements",
                count=recent_announcements,
                href="/youth/announcements",
                color="bg-blue-500",
                emoji="📢"
            ),
            QuickAction(
                title="Give Feedback",
                count=pending_feedback,
                href="/youth/feedback",
                color="bg-green-500",
                emoji="💬"
            ),
            QuickAction(
                title="Upcoming Events",
                count=upcoming_events,
                href="/youth/calendar",
                color="bg-purple-500",
                emoji="📅"
            ),
            QuickAction(
                title="Documents",
                count=available_documents,
                href="/youth/documents",
                color="bg-orange-500",
                emoji="📁"
            )
        ]
        
        # Community statistics
        total_youth = self.db.query(FamilyMember).count()
        total_activities_this_month = self.db.query(Activity).filter(
            and_(
                extract('year', Activity.date) == now.year,
                extract('month', Activity.date) == now.month
            )
        ).count()
        
        completed_activities = self.db.query(Activity).filter(
            Activity.status == ActivityStatusEnum.completed
        ).count()
        
        # Calculate engagement rate based on completed activities vs total youth
        engagement_rate = round((completed_activities / total_youth * 100), 0) if total_youth > 0 else 0
        
        community_stats = [
            CommunityStat(
                title="Active Youth",
                value=str(total_youth),
                emoji="👥",
                description="Growing strong!"
            ),
            CommunityStat(
                title="This Month",
                value=str(total_activities_this_month),
                emoji="🎉",
                description="Amazing events"
            ),
            CommunityStat(
                title="Completed",
                value=str(completed_activities),
                emoji="✅",
                description="Activities done"
            ),
            CommunityStat(
                title="Engagement",
                value=f"{engagement_rate}%",
                emoji="⭐",
                description="Super active!"
            )
        ]
        
        # Get real recent updates from announcements and activities
        recent_announcements_detailed = self.db.query(Announcement).order_by(
            Announcement.created_at.desc()
        ).limit(4).all()
        
        recent_activities_detailed = self.db.query(Activity).filter(
            Activity.date >= now.date() - timedelta(days=7)
        ).order_by(Activity.created_at.desc()).limit(2).all()
        
        recent_updates = []
        
        # Add announcements
        for announcement in recent_announcements_detailed:
            now_utc = datetime.now(timezone.utc)
            announcement_created_at = announcement.created_at.replace(tzinfo=timezone.utc) if announcement.created_at.tzinfo is None else announcement.created_at
            time_diff = now_utc - announcement_created_at
            if time_diff.days > 0:
                time_str = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                minutes = max(1, time_diff.seconds // 60)
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            
            # Determine urgency based on announcement type
            urgent = announcement.type.value == "important"
            
            # Select emoji based on content
            emoji = "🔥" if urgent else "📢"
            if "retreat" in announcement.title.lower():
                emoji = "🏕️"
            elif "feedback" in announcement.title.lower():
                emoji = "💕"
            elif "service" in announcement.title.lower():
                emoji = "🌟"
            elif "worship" in announcement.title.lower() or "song" in announcement.title.lower():
                emoji = "🎶"
            
            recent_updates.append(YouthUpdate(
                id=announcement.id,
                title=announcement.title,
                time=time_str,
                type="announcement",
                urgent=urgent,
                emoji=emoji
            ))
        
        # Add activities as events
        for activity in recent_activities_detailed:
            now_utc = datetime.now(timezone.utc)
            activity_created_at = activity.created_at.replace(tzinfo=timezone.utc) if activity.created_at.tzinfo is None else activity.created_at
            time_diff = now_utc - activity_created_at
            if time_diff.days > 0:
                time_str = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            else:
                time_str = "Recently scheduled"
                
            recent_updates.append(YouthUpdate(
                id=activity.id + 1000,  # Offset to avoid ID conflicts
                title=f"{activity.description} - {activity.date.strftime('%A')}",
                time=time_str,
                type="event",
                urgent=activity.status.value == "planned",
                emoji="🗓️"
            ))
        
        # Sort all updates by most recent first
        recent_updates = sorted(recent_updates, key=lambda x: x.id, reverse=True)[:4]
        
        # If no real data, provide empty list instead of mock data
        if not recent_updates:
            recent_updates = []
        
        return YouthDashboardData(
            quick_actions=quick_actions,
            community_stats=community_stats,
            recent_updates=recent_updates,
            last_updated=datetime.now(timezone.utc)
        )