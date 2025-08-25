from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime


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


class DashboardFilters(BaseModel):
    department_filter: str = "all"  # "all", "active", "pending"
    date_range: str = "6months"  # "1month", "3months", "6months", "1year"