from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date
from enum import Enum

class TrendEnum(str, Enum):
    up = "up"
    down = "down"
    stable = "stable"

class PerformanceLevelEnum(str, Enum):
    excellent = "excellent"
    good = "good"
    needs_improvement = "needs_improvement"

# Overall Performance Metrics
class OverallPerformanceMetrics(BaseModel):
    participation_rate: float
    program_completion: float
    family_engagement: float
    youth_retention: float
    trend: TrendEnum

# Family-specific Performance
class FamilyPerformanceMetrics(BaseModel):
    family_id: int
    family_name: str
    participation: float
    completion: float
    engagement: float
    activities_completed: int
    hours_logged: float
    trend: TrendEnum
    last_active: date
    performance_level: PerformanceLevelEnum

# Program Statistics
class ProgramStats(BaseModel):
    enrollment: float
    completion: float
    average_score: float
    trend: TrendEnum

class ProgramStatistics(BaseModel):
    bcc_program: ProgramStats
    fhe_program: ProgramStats
    service_projects: ProgramStats
    youth_activities: ProgramStats

# Complete Analytics Response
class ChurchPerformanceAnalytics(BaseModel):
    overall: OverallPerformanceMetrics
    family_metrics: List[FamilyPerformanceMetrics]
    program_stats: ProgramStatistics

# Individual Program Performance
class ProgramPerformanceDetail(BaseModel):
    program_name: str
    program_type: str  # bcc, fhe, service, youth
    enrollment_count: int
    completion_count: int
    total_participants: int
    average_score: float
    trend: TrendEnum
    last_updated: date

# Activity Summary for Analytics
class ActivitySummary(BaseModel):
    total_activities: int
    completed_activities: int
    planned_activities: int
    ongoing_activities: int
    cancelled_activities: int
    spiritual_activities: int
    social_activities: int
    completion_rate: float

# Family Engagement Details
class FamilyEngagementDetail(BaseModel):
    family_id: int
    family_name: str
    total_members: int
    active_members: int
    recent_activities: int
    last_activity_date: Optional[date]
    engagement_score: float
    participation_trend: TrendEnum

# Analytics Filters
class AnalyticsFilters(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    family_ids: Optional[List[int]] = None
    activity_categories: Optional[List[str]] = None
    include_inactive: bool = False

# Performance Insights
class PerformanceInsight(BaseModel):
    type: str  # "strength", "improvement", "recommendation"
    title: str
    description: str
    priority: str  # "high", "medium", "low"
    affected_families: Optional[List[str]] = None

class PerformanceInsights(BaseModel):
    strengths: List[PerformanceInsight]
    improvements: List[PerformanceInsight]
    recommendations: List[PerformanceInsight]

class CommissionCount(BaseModel):
    commission: str
    count: int

class CommissionDistribution(BaseModel):
    overall: List[CommissionCount]
    by_category: Dict[str, List[CommissionCount]]