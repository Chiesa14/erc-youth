from datetime import datetime, timezone
from typing import Optional

def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime"""
    return datetime.now(timezone.utc)

def make_aware(dt: Optional[datetime], tz=timezone.utc) -> Optional[datetime]:
    """Convert naive datetime to timezone-aware"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime is in UTC timezone"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)