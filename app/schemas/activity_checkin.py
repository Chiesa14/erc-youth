from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel


class ActivityCheckinSessionOut(BaseModel):
    activity_id: int
    token: str
    checkin_url: str
    is_active: bool
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class PublicCheckinInfo(BaseModel):
    activity_id: int
    family_id: int
    family_name: str
    date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    checkin_status: str
    server_time: datetime
    opens_at: datetime
    closes_at: datetime
    seconds_until_open: Optional[int] = None
    seconds_until_close: Optional[int] = None


class ActivityAttendanceCreatePublic(BaseModel):
    attendee_name: str
    family_of_origin_id: Optional[int] = None


class ActivityAttendanceOut(BaseModel):
    id: int
    activity_id: int
    attendee_name: str
    family_of_origin_id: Optional[int] = None
    family_of_origin_name: Optional[str] = None
    created_at: datetime


class FamilyPublicOut(BaseModel):
    id: int
    name: str
    category: str
