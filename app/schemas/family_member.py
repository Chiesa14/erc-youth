from pydantic import BaseModel, EmailStr, field_serializer, computed_field
from typing import Optional, List, Dict
from datetime import date
from enum import Enum

from app.schemas.user import GenderEnum
from app.utils.timestamps import TimestampMixin

class AccessPermissionEnum(str, Enum):
    submit_reports = "submit_reports"
    view_activities = "view_activities"
    upload_documents = "upload_documents"
    manage_calendar = "manage_calendar"

class DelegatedAccessOut(BaseModel):
    member_id: int
    name: str
    permissions: List[AccessPermissionEnum]

class GrantAccessRequest(BaseModel):
    member_id: int
    permissions: List[AccessPermissionEnum]

class EducationLevelEnum(str, Enum):
    none = "None"
    primary = "Primary"
    secondary = "Secondary"
    tertiary = "Tertiary"
    other = "Other"

class EmploymentStatusEnum(str, Enum):
    employed = "Employed"
    unemployed = "Unemployed"
    student = "Student"
    retired = "Retired"
    other = "Other"

class GraduationModeEnum(str, Enum):
    online = "Online"
    physical = "Physical"

class BccClassStatusEnum(str, Enum):
    graduate = "Graduate"
    ongoing = "Ongoing"
    not_yet_started = "Not yet Started"

class ParentGuardianStatusEnum(str, Enum):
    both_parents = "Both Parents"
    one_parent = "One Parent"
    stepfamily = "Stepfamily"
    grandparents = "Grandparents"
    guardian = "Guardian (Non-relative)"
    none = "None"

class EmploymentTypeEnum(str, Enum):
    full_time_employed = "Full-Time Employed"
    full_time_self_employed = "Full-Time Self-Employed"
    freelance = "Freelance"
    part_time = "Part-Time"
    temporary = "Temporary"
    contract = "Contract for a Specific Period"
    unemployed = "Unemployed"
    student = "Student"

class FamilyMemberBase(BaseModel):
    name: str
    id_name: Optional[str] = None  # ID Name from docs
    deliverance_name: Optional[str] = None  # Deliverance/Spiritual name
    phone: str  # required
    email: Optional[EmailStr] = None  # optional
    profile_photo: Optional[str] = None  # Path to uploaded profile photo
    
    # Residence details (district/sector/cell/village)
    home_address: Optional[str] = None
    district: Optional[str] = None
    sector: Optional[str] = None
    cell: Optional[str] = None
    village: Optional[str] = None
    living_arrangement: Optional[str] = None  # e.g., "with family", "alone"
    
    date_of_birth: date
    gender: GenderEnum
    
    # BCC Classes
    education_level: Optional[EducationLevelEnum] = None
    bcc_class_participation: Optional[bool] = None
    bcc_class_status: Optional[BccClassStatusEnum] = None
    year_of_graduation: Optional[int] = None
    graduation_mode: Optional[GraduationModeEnum] = None
    
    # Commission and Parent/Guardian
    commission: Optional[str] = None  # Church commission assignment
    parent_guardian_status: Optional[ParentGuardianStatusEnum] = None
    parental_status: Optional[bool] = None  # Keep for backwards compatibility
    
    # Occupation - detailed fields per docs
    employment_status: Optional[str] = None
    employment_type: Optional[EmploymentTypeEnum] = None
    job_title: Optional[str] = None
    organization: Optional[str] = None
    business_type: Optional[str] = None
    business_name: Optional[str] = None
    work_type: Optional[str] = None  # For freelance
    work_description: Optional[str] = None
    work_location: Optional[str] = None
    
    # Student fields
    institution: Optional[str] = None
    program: Optional[str] = None
    student_level: Optional[str] = None
    
    family_id: Optional[int] = None

class FamilyMemberCreate(FamilyMemberBase):
    family_id: Optional[int]= None

class FamilyMemberUpdate(FamilyMemberBase):
    pass

class FamilyMemberOut(FamilyMemberBase, TimestampMixin):
    id: int
    family_id: int

    class Config:
        from_attributes = True

    @computed_field
    def age(self) -> int:
        today = date.today()
        return (
            today.year - self.date_of_birth.year -
            ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

class MemberActivationRequest(BaseModel):
    member_id: int
    temp_password: str
    new_password: str

class MemberActivationResponse(BaseModel):
    message: str
    user_id: int

class AgeDistribution(BaseModel):
    twenty_to_twenty_two: float
    twenty_three_to_twenty_five: float
    twenty_six_to_thirty: float
    thirty_one_to_thirty_five: float
    thirty_six_to_forty: float
    forty_plus: float

class MonthlyTrend(BaseModel):
    spiritual: int
    social: int

class FamilyStats(BaseModel):
    total_members:int
    monthly_members:int
    bcc_graduate: int
    bcc_graduate_percentage: float
    active_events:int
    weekly_events:int
    engagement:int
    age_distribution: AgeDistribution
    activity_trends: Dict[str, MonthlyTrend]