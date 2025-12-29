from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.family_activity import Activity
from app.models.family import Family
from app.schemas.activity_checkin import (
    PublicCheckinInfo,
    ActivityAttendanceCreatePublic,
    ActivityAttendanceOut,
    FamilyPublicOut,
)
import app.controllers.activity_checkin as crud_checkin


router = APIRouter(tags=["Public Check-in"])


@router.get("/activity-checkin/{token}", response_model=PublicCheckinInfo)
def get_public_checkin_info(token: str, db: Session = Depends(get_db)):
    session = crud_checkin.get_checkin_session_by_token(db, token)
    if not session or session.is_active is False:
        raise HTTPException(status_code=404, detail="Invalid or inactive check-in token")

    activity = (
        db.query(Activity)
        .options(joinedload(Activity.family))
        .filter(Activity.id == session.activity_id)
        .first()
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    now = datetime.now(timezone.utc)
    opens_at, closes_at = crud_checkin.compute_checkin_window(activity)

    if now < opens_at:
        status = "not_started"
        seconds_until_open = int((opens_at - now).total_seconds())
        seconds_until_close = None
    elif now > closes_at:
        status = "closed"
        seconds_until_open = None
        seconds_until_close = None
    else:
        status = "open"
        seconds_until_open = None
        seconds_until_close = int((closes_at - now).total_seconds())

    return PublicCheckinInfo(
        activity_id=activity.id,
        family_id=activity.family_id,
        family_name=activity.family.name if activity.family else "Unknown",
        date=activity.date,
        start_time=activity.start_time,
        end_time=activity.end_time,
        checkin_status=status,
        server_time=now,
        opens_at=opens_at,
        closes_at=closes_at,
        seconds_until_open=seconds_until_open,
        seconds_until_close=seconds_until_close,
    )


@router.post("/activity-checkin/{token}/attend", response_model=ActivityAttendanceOut)
def public_submit_attendance(
    token: str,
    payload: ActivityAttendanceCreatePublic,
    db: Session = Depends(get_db),
):
    session = crud_checkin.get_checkin_session_by_token(db, token)
    if not session or session.is_active is False:
        raise HTTPException(status_code=404, detail="Invalid or inactive check-in token")

    activity = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.id == session.activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    now = datetime.now(timezone.utc)
    opens_at, closes_at = crud_checkin.compute_checkin_window(activity)

    if now < opens_at:
        raise HTTPException(status_code=400, detail="Check-in is not open yet")
    if now > closes_at:
        raise HTTPException(status_code=400, detail="Check-in is closed")

    try:
        attendance = crud_checkin.create_attendance(
            db,
            activity_id=activity.id,
            attendee_name=payload.attendee_name,
            family_of_origin_id=payload.family_of_origin_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    family_name = None
    if attendance.family_of_origin_id:
        fam = db.query(Family).filter(Family.id == attendance.family_of_origin_id).first()
        family_name = fam.name if fam else None

    return ActivityAttendanceOut(
        id=attendance.id,
        activity_id=attendance.activity_id,
        attendee_name=attendance.attendee_name,
        family_of_origin_id=attendance.family_of_origin_id,
        family_of_origin_name=family_name,
        created_at=attendance.created_at,
    )


@router.get("/families", response_model=list[FamilyPublicOut])
def list_families_public(db: Session = Depends(get_db)):
    families = db.query(Family).order_by(Family.category.asc(), Family.name.asc()).all()
    return [FamilyPublicOut(id=f.id, name=f.name, category=f.category) for f in families]
