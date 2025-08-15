from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from collections import defaultdict

from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.family_activity import Activity
from app.models.user import User
from app.schemas.analytics import (
    ChurchPerformanceAnalytics,
    OverallPerformanceMetrics,
    FamilyPerformanceMetrics,
    ProgramStatistics,
    ProgramStats,
    TrendEnum,
    PerformanceLevelEnum,
    ActivitySummary,
    FamilyEngagementDetail,
    PerformanceInsights,
    PerformanceInsight
)
from app.schemas.family_activity import ActivityStatusEnum, ActivityCategoryEnum


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self._cache = {}  # Simple cache for expensive queries

    def get_church_performance_analytics(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        family_ids: Optional[List[int]] = None
    ) -> ChurchPerformanceAnalytics:
        """Get comprehensive church performance analytics"""
        
        # Set default date range (last 90 days)
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # Get overall metrics
        overall_metrics = self._calculate_overall_metrics(start_date, end_date, family_ids)
        
        # Get family-specific metrics
        family_metrics = self._calculate_family_metrics(start_date, end_date, family_ids)
        
        # Get program statistics
        program_stats = self._calculate_program_statistics(start_date, end_date, family_ids)
        
        return ChurchPerformanceAnalytics(
            overall=overall_metrics,
            family_metrics=family_metrics,
            program_stats=program_stats
        )

    def _calculate_overall_metrics(
        self, 
        start_date: date, 
        end_date: date, 
        family_ids: Optional[List[int]] = None
    ) -> OverallPerformanceMetrics:
        """Calculate overall performance metrics with improved logic"""
        
        # Build base query filters
        date_filter = and_(
            Activity.date >= start_date,
            Activity.date <= end_date
        )
        
        # Total families (filtered if family_ids provided)
        if family_ids:
            total_families = self.db.query(Family).filter(Family.id.in_(family_ids)).count()
            family_activity_filter = and_(date_filter, Activity.family_id.in_(family_ids))
        else:
            total_families = self.db.query(Family).count()
            family_activity_filter = date_filter
        
        # Families with activities in the period
        active_families = self.db.query(func.count(func.distinct(Activity.family_id))).filter(
            family_activity_filter
        ).scalar() or 0
        
        # Participation rate
        participation_rate = (active_families / total_families * 100) if total_families > 0 else 0
        
        # Program completion rate
        total_activities = self.db.query(Activity).filter(family_activity_filter).count()
        
        completed_activities = self.db.query(Activity).filter(
            and_(
                family_activity_filter,
                Activity.status == ActivityStatusEnum.completed
            )
        ).count()
        
        program_completion = (completed_activities / total_activities * 100) if total_activities > 0 else 0
        
        # Family engagement (based on activity frequency and variety)
        if active_families > 0:
            avg_activities_per_family = total_activities / active_families
            # Also consider activity variety
            unique_activity_types = self.db.query(func.count(func.distinct(Activity.type))).filter(
                family_activity_filter
            ).scalar() or 1
            
            # Scale engagement based on both frequency and variety
            family_engagement = min((avg_activities_per_family * 8) + (unique_activity_types * 2), 100)
        else:
            family_engagement = 0
        
        # Youth retention (members under 30 who are still active)
        youth_cutoff_date = date.today() - timedelta(days=30*365)
        
        if family_ids:
            total_youth = self.db.query(FamilyMember).filter(
                and_(
                    FamilyMember.date_of_birth >= youth_cutoff_date,
                    FamilyMember.family_id.in_(family_ids)
                )
            ).count()
            
            active_youth_families = self.db.query(func.count(func.distinct(FamilyMember.family_id))).filter(
                and_(
                    FamilyMember.date_of_birth >= youth_cutoff_date,
                    FamilyMember.family_id.in_(family_ids),
                    FamilyMember.family_id.in_(
                        self.db.query(Activity.family_id).filter(family_activity_filter).distinct()
                    )
                )
            ).scalar() or 0
        else:
            total_youth = self.db.query(FamilyMember).filter(
                FamilyMember.date_of_birth >= youth_cutoff_date
            ).count()
            
            active_youth_families = self.db.query(func.count(func.distinct(FamilyMember.family_id))).filter(
                and_(
                    FamilyMember.date_of_birth >= youth_cutoff_date,
                    FamilyMember.family_id.in_(
                        self.db.query(Activity.family_id).filter(date_filter).distinct()
                    )
                )
            ).scalar() or 0
        
        youth_retention = (active_youth_families / total_youth * 100) if total_youth > 0 else 100
        
        # Calculate trend (compare with previous period)
        prev_start = start_date - (end_date - start_date)
        prev_end = start_date
        prev_metrics = self._get_previous_period_metrics(prev_start, prev_end, family_ids)
        
        trend = self._calculate_trend(participation_rate, prev_metrics.get('participation_rate', 0))
        
        return OverallPerformanceMetrics(
            participation_rate=round(participation_rate, 1),
            program_completion=round(program_completion, 1),
            family_engagement=round(family_engagement, 1),
            youth_retention=round(youth_retention, 1),
            trend=trend
        )

    def _calculate_family_metrics(
        self, 
        start_date: date, 
        end_date: date, 
        family_ids: Optional[List[int]] = None
    ) -> List[FamilyPerformanceMetrics]:
        """Calculate metrics for each family with improved accuracy"""
        
        # Get families to analyze
        if family_ids:
            families = self.db.query(Family).filter(Family.id.in_(family_ids)).all()
        else:
            families = self.db.query(Family).all()
        
        family_metrics = []
        
        for family in families:
            # Get family activities in the period
            activities = self.db.query(Activity).filter(
                and_(
                    Activity.family_id == family.id,
                    Activity.date >= start_date,
                    Activity.date <= end_date
                )
            ).all()
            
            total_activities = len(activities)
            completed_activities = len([a for a in activities if a.status == ActivityStatusEnum.completed])
            
            # Calculate metrics with improved logic
            participation = self._calculate_family_participation_improved(family.id, start_date, end_date)
            completion = (completed_activities / total_activities * 100) if total_activities > 0 else 0
            engagement = self._calculate_family_engagement_improved(family.id, start_date, end_date)
            
            # Hours logged (estimate based on activity types)
            hours_logged = self._estimate_hours_logged(activities)
            
            # Last active date
            last_active = max([a.date for a in activities]) if activities else start_date
            
            # Calculate trend
            prev_start = start_date - (end_date - start_date)
            prev_end = start_date
            prev_participation = self._calculate_family_participation_improved(family.id, prev_start, prev_end)
            trend = self._calculate_trend(participation, prev_participation)
            
            # Performance level
            performance_level = self._get_performance_level(participation)
            
            family_metrics.append(FamilyPerformanceMetrics(
                family_id=family.id,
                family_name=family.name,
                participation=round(participation, 1),
                completion=round(completion, 1),
                engagement=round(engagement, 1),
                activities_completed=total_activities,  # Show ALL activities, not just completed
                hours_logged=round(hours_logged, 1),
                trend=trend,
                last_active=last_active,
                performance_level=performance_level
            ))
        
        return sorted(family_metrics, key=lambda x: x.participation, reverse=True)

    def _calculate_family_participation_improved(self, family_id: int, start_date: date, end_date: date) -> float:
        """Calculate participation rate for a specific family with improved logic"""
        
        # Get actual activities for this family
        actual_activities = self.db.query(Activity).filter(
            and_(
                Activity.family_id == family_id,
                Activity.date >= start_date,
                Activity.date <= end_date
            )
        ).count()
        
        # Calculate expected activities based on period length
        # More realistic expectation: 1 activity per week for active families
        weeks = max((end_date - start_date).days / 7, 1)
        expected_activities = weeks * 1  # 1 activity per week
        
        # Calculate participation rate
        participation_rate = min((actual_activities / expected_activities * 100), 100)
        
        # Bonus for consistency (activities spread across the period)
        if actual_activities > 0:
            activities = self.db.query(Activity).filter(
                and_(
                    Activity.family_id == family_id,
                    Activity.date >= start_date,
                    Activity.date <= end_date
                )
            ).all()
            
            # Check if activities are spread across different weeks
            activity_weeks = set()
            for activity in activities:
                week_number = activity.date.isocalendar()[1]
                activity_weeks.add(week_number)
            
            consistency_bonus = min(len(activity_weeks) * 5, 20)  # Up to 20% bonus
            participation_rate = min(participation_rate + consistency_bonus, 100)
        
        return participation_rate

    def _calculate_family_engagement_improved(self, family_id: int, start_date: date, end_date: date) -> float:
        """Calculate engagement score for a specific family with improved logic"""
        
        activities = self.db.query(Activity).filter(
            and_(
                Activity.family_id == family_id,
                Activity.date >= start_date,
                Activity.date <= end_date
            )
        ).all()
        
        if not activities:
            return 0
        
        # Frequency score (30 points max)
        frequency_score = min(len(activities) * 3, 30)
        
        # Variety score (25 points max) - different activity types
        unique_types = len(set(a.type for a in activities))
        variety_score = min(unique_types * 5, 25)
        
        # Category diversity score (15 points max) - spiritual vs social
        unique_categories = len(set(a.category for a in activities))
        category_score = min(unique_categories * 7.5, 15)
        
        # Completion score (30 points max)
        completed = len([a for a in activities if a.status == ActivityStatusEnum.completed])
        completion_score = (completed / len(activities)) * 30
        
        total_score = frequency_score + variety_score + category_score + completion_score
        return min(total_score, 100)

    def _calculate_program_statistics(
        self, 
        start_date: date, 
        end_date: date, 
        family_ids: Optional[List[int]] = None
    ) -> ProgramStatistics:
        """Calculate statistics for different program types with improved mapping"""
        
        # Updated program mapping based on actual activity types
        program_mapping = {
            'bcc_program': ['Prayer calendars', 'Overnights'],  # BCC-related activities
            'fhe_program': ['Agape events'],  # Family Home Evening
            'service_projects': ['Contributions', 'Illnesses', 'Bereavements'],  # Service
            'youth_activities': ['Crusades', 'Weddings', 'Transfers']  # Youth activities
        }
        
        program_stats = {}
        
        for program_name, activity_types in program_mapping.items():
            stats = self._calculate_program_stats_improved(
                activity_types, start_date, end_date, family_ids, calculate_trend=True
            )
            program_stats[program_name] = stats
        
        return ProgramStatistics(
            bcc_program=program_stats['bcc_program'],
            fhe_program=program_stats['fhe_program'],
            service_projects=program_stats['service_projects'],
            youth_activities=program_stats['youth_activities']
        )

    def _calculate_program_stats_improved(
        self,
        activity_types: List[str],
        start_date: date,
        end_date: date,
        family_ids: Optional[List[int]] = None,
        calculate_trend: bool = True
    ) -> ProgramStats:
        """Calculate stats for a specific program with improved logic"""
        
        # Build query filters
        date_filter = and_(
            Activity.date >= start_date,
            Activity.date <= end_date,
            Activity.type.in_(activity_types)
        )
        
        if family_ids:
            program_filter = and_(date_filter, Activity.family_id.in_(family_ids))
            total_families = self.db.query(Family).filter(Family.id.in_(family_ids)).count()
        else:
            program_filter = date_filter
            total_families = self.db.query(Family).count()
        
        # Families enrolled in this program (have activities of these types)
        enrolled_families = self.db.query(func.count(func.distinct(Activity.family_id))).filter(
            program_filter
        ).scalar() or 0
        
        # Activities in this program
        program_activities = self.db.query(Activity).filter(program_filter).all()
        
        total_activities = len(program_activities)
        completed_activities = len([a for a in program_activities if a.status == ActivityStatusEnum.completed])
        
        # Calculate metrics
        enrollment = (enrolled_families / total_families * 100) if total_families > 0 else 0
        completion = (completed_activities / total_activities * 100) if total_activities > 0 else 0
        
        # Average score (weighted combination of enrollment and completion)
        average_score = (enrollment * 0.4) + (completion * 0.6)  # Completion weighted more heavily
        
        # Calculate trend (only if requested to avoid infinite recursion)
        trend = TrendEnum.stable
        if calculate_trend:
            prev_start = start_date - (end_date - start_date)
            prev_end = start_date
            
            # Prevent recursion by not calculating trend for previous period
            prev_stats = self._calculate_program_stats_improved(
                activity_types, prev_start, prev_end, family_ids, calculate_trend=False
            )
            trend = self._calculate_trend(average_score, prev_stats.average_score)
        
        return ProgramStats(
            enrollment=round(enrollment, 1),
            completion=round(completion, 1),
            average_score=round(average_score, 1),
            trend=trend
        )

    def _estimate_hours_logged(self, activities: List[Activity]) -> float:
        """Estimate hours logged based on activity types and status"""
        
        # Hour estimates by activity type
        hour_estimates = {
            'Prayer calendars': 1.5,
            'Overnights': 8.0,
            'Crusades': 6.0,
            'Agape events': 3.0,
            'Contributions': 1.5,
            'Illnesses': 2.0,
            'Bereavements': 4.0,
            'Weddings': 6.0,
            'Transfers': 1.0
        }

        # Status multipliers for hours calculation
        status_multipliers = {
            ActivityStatusEnum.completed: 1.0,    # Full hours for completed
            ActivityStatusEnum.ongoing: 0.7,      # 70% hours for ongoing
            ActivityStatusEnum.planned: 0.0,      # No hours for planned (not started)
            ActivityStatusEnum.cancelled: 0.0     # No hours for cancelled
        }
        
        total_hours = 0
        for activity in activities:
            base_hours = hour_estimates.get(activity.type, 1.0)
            multiplier = status_multipliers.get(activity.status, 0.0)
            total_hours += base_hours * multiplier
        
        return total_hours

    def _calculate_trend(self, current: float, previous: float) -> TrendEnum:
        """Calculate trend based on current vs previous values"""
        
        if previous == 0:
            return TrendEnum.up if current > 0 else TrendEnum.stable
        
        change_percent = ((current - previous) / previous) * 100
        
        if change_percent > 5:
            return TrendEnum.up
        elif change_percent < -5:
            return TrendEnum.down
        else:
            return TrendEnum.stable

    def _get_performance_level(self, score: float) -> PerformanceLevelEnum:
        """Get performance level based on score"""
        
        if score >= 85:
            return PerformanceLevelEnum.excellent
        elif score >= 65:
            return PerformanceLevelEnum.good
        else:
            return PerformanceLevelEnum.needs_improvement

    def _get_previous_period_metrics(
        self, 
        start_date: date, 
        end_date: date, 
        family_ids: Optional[List[int]] = None
    ) -> Dict[str, float]:
        """Get metrics for the previous period for trend calculation"""
        
        date_filter = and_(
            Activity.date >= start_date,
            Activity.date <= end_date
        )
        
        if family_ids:
            total_families = self.db.query(Family).filter(Family.id.in_(family_ids)).count()
            active_families = self.db.query(func.count(func.distinct(Activity.family_id))).filter(
                and_(date_filter, Activity.family_id.in_(family_ids))
            ).scalar() or 0
        else:
            total_families = self.db.query(Family).count()
            active_families = self.db.query(func.count(func.distinct(Activity.family_id))).filter(
                date_filter
            ).scalar() or 0
        
        participation_rate = (active_families / total_families * 100) if total_families > 0 else 0
        
        return {
            'participation_rate': participation_rate
        }

    def get_performance_insights(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> PerformanceInsights:
        """Generate performance insights and recommendations"""
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        analytics = self.get_church_performance_analytics(start_date, end_date)
        
        strengths = []
        improvements = []
        recommendations = []
        
        # Analyze overall performance
        if analytics.overall.participation_rate >= 80:
            strengths.append(PerformanceInsight(
                type="strength",
                title="High Participation Rate",
                description=f"Excellent participation rate of {analytics.overall.participation_rate}%",
                priority="high"
            ))
        
        if analytics.overall.program_completion >= 85:
            strengths.append(PerformanceInsight(
                type="strength",
                title="Strong Program Completion",
                description=f"High completion rate of {analytics.overall.program_completion}%",
                priority="high"
            ))
        
        # Identify areas for improvement
        low_performing_families = [
            f.family_name for f in analytics.family_metrics 
            if f.performance_level == PerformanceLevelEnum.needs_improvement
        ]
        
        if low_performing_families:
            improvements.append(PerformanceInsight(
                type="improvement",
                title="Low Engagement Families",
                description="Some families showing declining engagement",
                priority="high",
                affected_families=low_performing_families
            ))
        
        # Generate recommendations
        if analytics.overall.youth_retention < 85:
            recommendations.append(PerformanceInsight(
                type="recommendation",
                title="Youth Engagement Program",
                description="Implement targeted youth activities to improve retention",
                priority="medium"
            ))
        
        if analytics.overall.participation_rate < 70:
            recommendations.append(PerformanceInsight(
                type="recommendation",
                title="Increase Family Outreach",
                description="Consider additional outreach programs to boost participation",
                priority="high"
            ))
        
        return PerformanceInsights(
            strengths=strengths,
            improvements=improvements,
            recommendations=recommendations
        )