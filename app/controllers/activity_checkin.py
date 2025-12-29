from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import secrets
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.family_activity import Activity
from app.models.family_activity_checkin import ActivityCheckinSession, ActivityAttendance
from app.models.family import Family


def _generate_unique_token(db: Session) -> str:
    for _ in range(10):
        token = secrets.token_urlsafe(32)
        exists = db.query(ActivityCheckinSession).filter(ActivityCheckinSession.token == token).first()
        if not exists:
            return token
    raise RuntimeError("Unable to generate unique token")


def compute_checkin_window(activity: Activity) -> tuple[datetime, datetime]:
    start_t = activity.start_time or time(0, 0)
    if activity.end_time:
        end_t = activity.end_time
    else:
        end_t = time(23, 59, 59)

    opens_at = datetime.combine(activity.date, start_t, tzinfo=timezone.utc)
    closes_at = datetime.combine(activity.date, end_t, tzinfo=timezone.utc)

    if closes_at < opens_at:
        closes_at = closes_at + timedelta(days=1)

    return opens_at, closes_at


def upsert_checkin_session(db: Session, activity: Activity) -> ActivityCheckinSession:
    session = db.query(ActivityCheckinSession).filter(ActivityCheckinSession.activity_id == activity.id).first()

    opens_at, closes_at = compute_checkin_window(activity)

    if session:
        session.valid_from = opens_at
        session.valid_until = closes_at
        if not session.token:
            session.token = _generate_unique_token(db)
        if session.is_active is None:
            session.is_active = True
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    token = _generate_unique_token(db)
    session = ActivityCheckinSession(
        activity_id=activity.id,
        token=token,
        is_active=True,
        valid_from=opens_at,
        valid_until=closes_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def build_checkin_url(token: str) -> str:
    base = (settings.FRONTEND_URL or "").strip()
    if base.endswith("/"):
        base = base[:-1]

    if not (base.startswith("http://") or base.startswith("https://")):
        base = f"https://{base.lstrip('/')}"

    return f"{base}/checkin/{token}"


def get_activity_by_checkin_token(db: Session, token: str) -> Optional[Activity]:
    session = db.query(ActivityCheckinSession).filter(ActivityCheckinSession.token == token).first()
    if not session:
        return None

    activity = (
        db.query(Activity)
        .options(joinedload(Activity.family))
        .filter(Activity.id == session.activity_id)
        .first()
    )
    return activity


def get_checkin_session_by_token(db: Session, token: str) -> Optional[ActivityCheckinSession]:
    return db.query(ActivityCheckinSession).filter(ActivityCheckinSession.token == token).first()


def create_attendance(
    db: Session,
    *,
    activity_id: int,
    attendee_name: str,
    family_of_origin_id: Optional[int],
) -> ActivityAttendance:
    attendee_name = attendee_name.strip()
    if not attendee_name:
        raise ValueError("Attendee name is required")

    if family_of_origin_id is not None:
        family = db.query(Family).filter(Family.id == family_of_origin_id).first()
        if not family:
            raise ValueError("Family of origin not found")

    attendance = ActivityAttendance(
        activity_id=activity_id,
        attendee_name=attendee_name,
        family_of_origin_id=family_of_origin_id,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return attendance


def list_attendances_for_activity(db: Session, activity_id: int) -> list[ActivityAttendance]:
    return (
        db.query(ActivityAttendance)
        .options(joinedload(ActivityAttendance.family_of_origin))
        .filter(ActivityAttendance.activity_id == activity_id)
        .order_by(ActivityAttendance.created_at.asc())
        .all()
    )
