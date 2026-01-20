from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime


# Church Dashboard Schemas (existing)
class OverallStats(BaseModel):
    total_youth: int
    total_families: int
    male_ratio: float
    female_ratio: float
    bcc_completion: float
    program_implementation: float
    active_programs: int
    pending_approvals: int


class DepartmentData(BaseModel):
    name: str
    youth: int
    completion: float
    implementation: float


class GenderDistribution(BaseModel):
    name: str
    value: float
    color: str


class MonthlyProgress(BaseModel):
    month: str
    implementation: float
    bcc: float


class AgeDistributionData(BaseModel):
    age_group: str
    percentage: float
 

class ChurchDashboardData(BaseModel):
    overall_stats: OverallStats
    department_data: List[DepartmentData]
    gender_distribution: List[GenderDistribution]
    monthly_progress: List[MonthlyProgress]
    age_distribution: List[AgeDistributionData]
    last_updated: datetime


# Admin Dashboard Schemas
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    new_users_this_month: int
    new_users_last_month: int
    reports_submitted: int
    active_families: int
    total_users_change: str
    new_users_change: str


class RecentActivity(BaseModel):
    user: str
    action: str
    time: str
    type: str
    user_id: Optional[int] = None
    family_id: Optional[int] = None
    family_name: Optional[str] = None
    table_name: Optional[str] = None
    record_id: Optional[int] = None
    details: Optional[str] = None


class AdminDashboardData(BaseModel):
    stats: AdminStats
    user_gender_distribution: List[GenderDistribution]
    youth_members_count: int
    youth_members_young_count: int
    youth_members_mature_count: int
    youth_members_target: int
    youth_members_progress_percent: float
    recent_activities: List[RecentActivity]
    last_updated: datetime


# Parent Dashboard Schemas
class FamilyAgeDistribution(BaseModel):
    twenty_to_twenty_two: int
    twenty_three_to_twenty_five: int
    twenty_six_to_thirty: int
    thirty_one_to_thirty_five: int
    thirty_six_to_forty: int
    forty_plus: int


class MonthlyTrend(BaseModel):
    spiritual: int
    social: int


class FamilyStats(BaseModel):
    total_members: int
    monthly_members: int
    bcc_graduate: int
    bcc_graduate_percentage: float
    active_events: int
    weekly_events: int
    engagement: int
    age_distribution: FamilyAgeDistribution
    activity_trends: Dict[str, MonthlyTrend]


class ParentDashboardData(BaseModel):
    family_stats: FamilyStats
    last_updated: datetime


# Youth Dashboard Schemas
class QuickAction(BaseModel):
    title: str
    count: int
    href: str
    color: str
    emoji: str


class CommunityStat(BaseModel):
    title: str
    value: str
    emoji: str
    description: str


class YouthUpdate(BaseModel):
    id: int
    title: str
    time: str
    type: str
    urgent: bool
    emoji: str


class YouthDashboardData(BaseModel):
    quick_actions: List[QuickAction]
    community_stats: List[CommunityStat]
    recent_updates: List[YouthUpdate]
    last_updated: datetime


# Common Filters
class DashboardFilters(BaseModel):
    department_filter: str = "all"  # "all", "active", "pending"
    date_range: str = "6months"  # "1month", "3months", "6months", "1year"