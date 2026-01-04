from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, and_
from sqlalchemy.orm import Session, joinedload
from typing import Optional, Literal
from datetime import date, datetime, time
from app.api.routes.family_member import require_parent
from app.db.session import get_db
from app.models.user import User
from app.models.family_activity import Activity
from app.core.security import get_current_active_user
import app.controllers.family_activity as crud_activity
import app.schemas.family_activity as activity_schema
from app.schemas.user import RoleEnum
from app.schemas.activity_checkin import ActivityCheckinSessionOut, ActivityAttendanceOut
from app.core.config import settings
import app.controllers.activity_checkin as crud_checkin
from app.models.family_activity_checkin import ActivityCheckinSession
from app.utils.timestamps import (
    parse_timestamp_filters,
    apply_timestamp_filters,
    apply_timestamp_sorting
)

router = APIRouter(tags=["Activities"])


def _coalesced_start_date_col():
    return func.coalesce(Activity.start_date, Activity.date)


def _coalesced_end_date_col():
    return func.coalesce(Activity.end_date, Activity.date)


def _normalize_activity_dates(
    *,
    date_value: Optional[date],
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[date, date, date]:
    if start_date is not None or end_date is not None:
        if start_date is None:
            raise HTTPException(status_code=400, detail="start_date is required when providing an end_date")
        normalized_end = end_date or start_date
        if normalized_end < start_date:
            raise HTTPException(status_code=400, detail="end_date cannot be before start_date")
        legacy_date = start_date
        return start_date, normalized_end, legacy_date

    if date_value is None:
        raise HTTPException(status_code=400, detail="Either date or start_date must be provided")

    return date_value, date_value, date_value


def _activity_start_datetime(activity_date: date, start_time: Optional[time]) -> datetime:
    return datetime.combine(activity_date, start_time or time(0, 0))


def _activity_end_datetime(activity_date: date, end_time: Optional[time]) -> datetime:
    return datetime.combine(activity_date, end_time or time(23, 59, 59))


def _compute_initial_status(
    start_date: date,
    end_date: date,
    start_time: Optional[time],
    end_time: Optional[time],
) -> activity_schema.ActivityStatusEnum:
    now = datetime.now()
    start_dt = _activity_start_datetime(start_date, start_time)
    end_dt = _activity_end_datetime(end_date, end_time)

    if now > end_dt:
        raise HTTPException(status_code=400, detail="Cannot create an activity whose end time is in the past.")

    return (
        activity_schema.ActivityStatusEnum.planned
        if now < start_dt
        else activity_schema.ActivityStatusEnum.ongoing
    )


def _maybe_promote_planned_to_ongoing(db: Session, activities: list[Activity]) -> None:
    now = datetime.now()
    changed = False
    for a in activities:
        if a.status == activity_schema.ActivityStatusEnum.planned:
            activity_start = a.start_date or a.date
            if now >= _activity_start_datetime(activity_start, a.start_time):
                a.status = activity_schema.ActivityStatusEnum.ongoing
                changed = True

    if changed:
        db.commit()
        for a in activities:
            db.refresh(a)


def require_pastor_or_parent(current_user: User):
    """Helper function to check if user is pastor or parent"""
    if current_user.role not in [RoleEnum.church_pastor, RoleEnum.mere, RoleEnum.pere]:
        raise HTTPException(
            status_code=403,
            detail="Only pastors and parents can access this resource"
        )


# POST route - create activity
@router.post("/", response_model=activity_schema.ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
        activity: activity_schema.ActivityCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)
    today = date.today()

    start_date, end_date, legacy_date = _normalize_activity_dates(
        date_value=activity.date,
        start_date=activity.start_date,
        end_date=activity.end_date,
    )

    if start_date < today:
        raise HTTPException(status_code=400, detail="Cannot create an activity in the past.")

    if not activity.family_id:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User is not assigned to a family.")
        activity_data = activity.model_copy(update={"family_id": current_user.family_id})
    else:
        activity_data = activity

    activity_data = activity_data.model_copy(
        update={
            "date": legacy_date,
            "start_date": start_date,
            "end_date": end_date,
            "status": _compute_initial_status(start_date, end_date, activity_data.start_time, activity_data.end_time)
        }
    )
    return crud_activity.create_activity(db, activity_data)


# SPECIFIC ROUTES FIRST - these must come before /{activity_id}
@router.get("/all", response_model=list[activity_schema.ActivityOut])
def read_all_activities(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        date_from: Optional[date] = Query(None),
        date_to: Optional[date] = Query(None),
        activity_date: Optional[date] = Query(None),
        family_id: Optional[int] = Query(None),
        status: Optional[str] = Query(None),
        category: Optional[str] = Query(None),
        created_after: Optional[str] = Query(None),
        created_before: Optional[str] = Query(None),
        updated_after: Optional[str] = Query(None),
        updated_before: Optional[str] = Query(None),
        sort_by: Optional[str] = Query(None, enum=["created_at", "updated_at", "date", "family_id"]),
        sort_order: Optional[str] = Query("desc", enum=["asc", "desc"]),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
):
    if current_user.role not in [RoleEnum.church_pastor, RoleEnum.mere, RoleEnum.pere, RoleEnum.other, RoleEnum.admin]:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to access activities",
        )

    # Build base query with joinedload to include family name
    query = db.query(Activity).options(joinedload(Activity.family))

    if current_user.role == RoleEnum.church_pastor:
        if family_id:
            query = query.filter(Activity.family_id == family_id)
    elif current_user.role in [RoleEnum.other, RoleEnum.admin]:
        if family_id:
            query = query.filter(Activity.family_id == family_id)
    else:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User is not assigned to a family.")
        query = query.filter(Activity.family_id == current_user.family_id)

    # Apply date filters (overlap semantics for ranges)
    start_col = _coalesced_start_date_col()
    end_col = _coalesced_end_date_col()
    if activity_date:
        query = query.filter(and_(start_col <= activity_date, end_col >= activity_date))
    else:
        if date_from:
            query = query.filter(end_col >= date_from)
        if date_to:
            query = query.filter(start_col <= date_to)

    # Apply status filter
    if status:
        query = query.filter(Activity.status == status)

    # Apply category filter
    if category:
        query = query.filter(Activity.category == category)

    # Apply timestamp filters
    has_timestamp_filters = any([created_after, created_before, updated_after, updated_before])
    if has_timestamp_filters:
        filters = parse_timestamp_filters(created_after, created_before, updated_after, updated_before)
        query = apply_timestamp_filters(query, Activity, filters)

    # Apply sorting
    if sort_by:
        if sort_by == "date":
            query = query.order_by(start_col.asc() if sort_order == "asc" else start_col.desc())
        elif sort_by == "family_id":
            query = query.order_by(Activity.family_id.asc() if sort_order == "asc" else Activity.family_id.desc())
        else:
            query = apply_timestamp_sorting(query, Activity, sort_by, sort_order)
    else:
        query = query.order_by(start_col.desc(), Activity.family_id.asc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Get activities and convert to Pydantic models
    activities = query.all()
    _maybe_promote_planned_to_ongoing(db, activities)
    return crud_activity.convert_activities_to_out(activities)


@router.get("/stats", response_model=dict)
def get_activity_statistics(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        family_id: Optional[int] = Query(None),
):
    require_pastor_or_parent(current_user)

    # Build base query with joinedload to include family name
    query = db.query(Activity).options(joinedload(Activity.family))

    # Apply family restrictions
    if current_user.role == RoleEnum.church_pastor:
        if family_id:
            query = query.filter(Activity.family_id == family_id)
    else:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User is not assigned to a family.")
        query = query.filter(Activity.family_id == current_user.family_id)

    # Get all activities for calculations
    activities = query.all()

    # Calculate statistics
    from datetime import datetime, timedelta
    from collections import defaultdict

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    stats = {
        "total_activities": len(activities),
        "by_status": defaultdict(int),
        "by_category": defaultdict(int),
        "this_week": 0,
        "upcoming": 0,
        "overdue": 0,
        "by_family": defaultdict(int),  # Will store family names instead of IDs
    }

    for activity in activities:
        activity_start = activity.start_date or activity.date
        activity_end = activity.end_date or activity.date

        # Count by status
        stats["by_status"][activity.status] += 1

        # Count by category
        stats["by_category"][activity.category] += 1

        # Count by family name
        family_name = activity.family.name if activity.family else "Unknown"
        stats["by_family"][family_name] += 1

        # This week activities (overlap semantics)
        if activity_end >= week_start and activity_start <= week_end:
            stats["this_week"] += 1

        # Upcoming activities
        if activity_start > today:
            stats["upcoming"] += 1

        # Overdue activities
        if activity_end < today and activity.status in ["Planned", "Ongoing"]:
            stats["overdue"] += 1

    # Convert defaultdicts to regular dicts
    stats["by_status"] = dict(stats["by_status"])
    stats["by_category"] = dict(stats["by_category"])
    stats["by_family"] = dict(stats["by_family"])

    return stats


@router.get("/type-status-summary", response_model=list[dict])
def get_activity_type_status_summary(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        family_id: Optional[int] = Query(None),
        date_from: Optional[date] = Query(None),
        date_to: Optional[date] = Query(None),
        date_field: Literal["activity_date", "created_at", "updated_at"] = Query("activity_date"),
):
    require_pastor_or_parent(current_user)

    query = db.query(
        Activity.type,
        Activity.status,
        func.count(Activity.id).label("count"),
    )

    if current_user.role == RoleEnum.church_pastor:
        if family_id:
            query = query.filter(Activity.family_id == family_id)
    else:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User is not assigned to a family.")
        query = query.filter(Activity.family_id == current_user.family_id)

    if date_field == "activity_date":
        if date_from:
            query = query.filter(_coalesced_end_date_col() >= date_from)
        if date_to:
            query = query.filter(_coalesced_start_date_col() <= date_to)
    elif date_field == "created_at":
        created_date_col = func.date(Activity.created_at)
        if date_from:
            query = query.filter(created_date_col >= date_from)
        if date_to:
            query = query.filter(created_date_col <= date_to)
    else:  # updated_at
        updated_date_col = func.date(Activity.updated_at)
        if date_from:
            query = query.filter(updated_date_col >= date_from)
        if date_to:
            query = query.filter(updated_date_col <= date_to)

    query = query.group_by(Activity.type, Activity.status)

    rows = query.all()

    known_types: list[str] = [
        *[t.value for t in activity_schema.SpiritualTypeEnum],
        *[t.value for t in activity_schema.SocialTypeEnum],
    ]

    by_type = {
        t: {
            "type": t,
            "planned": 0,
            "ongoing": 0,
            "completed": 0,
        }
        for t in known_types
    }

    for row in rows:
        activity_type = row.type
        status_value = row.status.value if hasattr(row.status, "value") else str(row.status)

        if activity_type not in by_type:
            by_type[activity_type] = {
                "type": activity_type,
                "planned": 0,
                "ongoing": 0,
                "completed": 0,
            }

        if status_value == activity_schema.ActivityStatusEnum.planned.value:
            by_type[activity_type]["planned"] += row.count
        elif status_value == activity_schema.ActivityStatusEnum.ongoing.value:
            by_type[activity_type]["ongoing"] += row.count
        elif status_value == activity_schema.ActivityStatusEnum.completed.value:
            by_type[activity_type]["completed"] += row.count

    ordered: list[dict] = [by_type[t] for t in known_types if t in by_type]
    extra = sorted(
        (v for k, v in by_type.items() if k not in known_types),
        key=lambda x: x["type"],
    )
    return [*ordered, *extra]


@router.get("/family/{family_id}", response_model=list[activity_schema.ActivityOut])
def read_activities_for_family(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        date_from: Optional[date] = Query(None),
        date_to: Optional[date] = Query(None),
        activity_date: Optional[date] = Query(None),
        created_after: Optional[str] = Query(None),
        created_before: Optional[str] = Query(None),
        updated_after: Optional[str] = Query(None),
        updated_before: Optional[str] = Query(None),
        sort_by: Optional[str] = Query(None, enum=["created_at", "updated_at", "date"]),
        sort_order: Optional[str] = Query("desc", enum=["asc", "desc"]),
):
    if current_user.role == RoleEnum.church_pastor:
        pass
    elif current_user.role in [RoleEnum.mere, RoleEnum.pere, RoleEnum.other, RoleEnum.admin]:
        if current_user.family_id != family_id:
            raise HTTPException(status_code=403, detail="Not authorized to view activities for this family.")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions to access family activities.")

    # Build base query with joinedload to include family name
    query = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.family_id == family_id)

    # Apply date filters (overlap semantics for ranges)
    start_col = _coalesced_start_date_col()
    end_col = _coalesced_end_date_col()
    if activity_date:
        query = query.filter(and_(start_col <= activity_date, end_col >= activity_date))
    else:
        if date_from:
            query = query.filter(end_col >= date_from)
        if date_to:
            query = query.filter(start_col <= date_to)

    # Apply timestamp filters
    has_timestamp_filters = any([created_after, created_before, updated_after, updated_before])
    if has_timestamp_filters:
        filters = parse_timestamp_filters(created_after, created_before, updated_after, updated_before)
        query = apply_timestamp_filters(query, Activity, filters)

    # Apply sorting
    if sort_by:
        if sort_by == "date":
            query = query.order_by(start_col.asc() if sort_order == "asc" else start_col.desc())
        else:
            query = apply_timestamp_sorting(query, Activity, sort_by, sort_order)
    else:
        query = query.order_by(start_col.desc())

    # Get activities and convert to Pydantic models
    activities = query.all()
    _maybe_promote_planned_to_ongoing(db, activities)
    return crud_activity.convert_activities_to_out(activities)


# PARAMETERIZED ROUTES LAST - these must come after specific routes
@router.get("/{activity_id}", response_model=activity_schema.ActivityOut)
def get_activity_by_id(
        activity_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    activity = crud_activity.get_activity_by_id(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if activity.status == activity_schema.ActivityStatusEnum.planned:
        activity_start = activity.start_date or activity.date
        if datetime.now() >= _activity_start_datetime(activity_start, activity.start_time):
            raw = db.query(Activity).filter(Activity.id == activity_id).first()
            if raw:
                raw.status = activity_schema.ActivityStatusEnum.ongoing
                db.commit()
                db.refresh(raw)
                activity = crud_activity.get_activity_by_id(db, activity_id)

    # Pastors can view any activity, parents only their family's activities
    if current_user.role == RoleEnum.church_pastor:
        pass  # Pastor can view any activity
    elif current_user.role == "parent":
        if current_user.family_id != activity.family_id:
            raise HTTPException(status_code=403, detail="Not authorized to view this activity")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions to view this activity")

    return activity


@router.put("/{activity_id}", response_model=activity_schema.ActivityOut)
def update_activity(
        activity_id: int,
        updated_data: activity_schema.ActivityUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    activity = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Only allow parents to update their own family's activities
    if current_user.family_id != activity.family_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this activity")

    update_payload = updated_data.dict(exclude_unset=True)

    if "date" in update_payload and update_payload["date"] is not None and update_payload["date"] < date.today():
        raise HTTPException(status_code=400, detail="Cannot set activity date in the past.")
    if "start_date" in update_payload and update_payload["start_date"] is not None and update_payload["start_date"] < date.today():
        raise HTTPException(status_code=400, detail="Cannot set activity start_date in the past.")

    if any(k in update_payload for k in ["date", "start_date", "end_date"]):
        start_date, end_date, legacy_date = _normalize_activity_dates(
            date_value=update_payload.get("date", activity.date),
            start_date=update_payload.get("start_date", activity.start_date),
            end_date=update_payload.get("end_date", activity.end_date),
        )
        update_payload["date"] = legacy_date
        update_payload["start_date"] = start_date
        update_payload["end_date"] = end_date

    if "status" in update_payload:
        current_status = activity.status
        new_status = update_payload["status"]

        if current_status == activity_schema.ActivityStatusEnum.completed:
            raise HTTPException(status_code=400, detail="Completed activities cannot be modified.")

        if current_status == activity_schema.ActivityStatusEnum.cancelled:
            raise HTTPException(status_code=400, detail="Cancelled activities cannot be modified.")

        allowed_next = {
            activity_schema.ActivityStatusEnum.planned: {
                activity_schema.ActivityStatusEnum.ongoing,
                activity_schema.ActivityStatusEnum.cancelled,
                activity_schema.ActivityStatusEnum.planned,
            },
            activity_schema.ActivityStatusEnum.ongoing: {
                activity_schema.ActivityStatusEnum.completed,
                activity_schema.ActivityStatusEnum.cancelled,
                activity_schema.ActivityStatusEnum.ongoing,
            },
        }

        if new_status not in allowed_next.get(current_status, set()):
            raise HTTPException(status_code=400, detail="Invalid status transition.")

        if new_status == activity_schema.ActivityStatusEnum.completed and current_status != activity_schema.ActivityStatusEnum.ongoing:
            raise HTTPException(status_code=400, detail="Only ongoing activities can be marked completed.")

    for field, value in update_payload.items():
        setattr(activity, field, value)

    if activity.status == activity_schema.ActivityStatusEnum.planned:
        activity_start = activity.start_date or activity.date
        if datetime.now() >= _activity_start_datetime(activity_start, activity.start_time):
            activity.status = activity_schema.ActivityStatusEnum.ongoing

    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(activity)

    # Refresh check-in window if date/time changed.
    crud_checkin.upsert_checkin_session(db, activity)

    # Convert to Pydantic model using the existing helper function
    return crud_activity.convert_activities_to_out([activity])[0]


@router.get("/{activity_id}/checkin-session", response_model=ActivityCheckinSessionOut)
def get_checkin_session(
        activity_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    activity = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if current_user.role not in [RoleEnum.church_pastor, RoleEnum.other]:
        if not current_user.family_id or current_user.family_id != activity.family_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this activity")

    session = db.query(ActivityCheckinSession).filter(ActivityCheckinSession.activity_id == activity.id).first()
    if not session:
        session = crud_checkin.upsert_checkin_session(db, activity)

    return ActivityCheckinSessionOut(
        activity_id=activity.id,
        token=session.token,
        checkin_url=crud_checkin.build_checkin_url(session.token),
        is_active=session.is_active,
        valid_from=session.valid_from,
        valid_until=session.valid_until,
    )


@router.post("/{activity_id}/checkin-session", response_model=ActivityCheckinSessionOut)
def create_or_refresh_checkin_session(
        activity_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    require_pastor_or_parent(current_user)

    activity = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if current_user.role != RoleEnum.church_pastor:
        if not current_user.family_id or current_user.family_id != activity.family_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this activity")

    session = crud_checkin.upsert_checkin_session(db, activity)
    return ActivityCheckinSessionOut(
        activity_id=activity.id,
        token=session.token,
        checkin_url=crud_checkin.build_checkin_url(session.token),
        is_active=session.is_active,
        valid_from=session.valid_from,
        valid_until=session.valid_until,
    )


@router.get("/{activity_id}/attendances", response_model=list[ActivityAttendanceOut])
def list_activity_attendances(
        activity_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    require_pastor_or_parent(current_user)

    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if current_user.role != RoleEnum.church_pastor:
        if not current_user.family_id or current_user.family_id != activity.family_id:
            raise HTTPException(status_code=403, detail="Not authorized to view attendances for this activity")

    attendances = crud_checkin.list_attendances_for_activity(db, activity_id)
    result: list[ActivityAttendanceOut] = []
    for a in attendances:
        result.append(
            ActivityAttendanceOut(
                id=a.id,
                activity_id=a.activity_id,
                attendee_name=a.attendee_name,
                family_of_origin_id=a.family_of_origin_id,
                family_of_origin_name=a.family_of_origin.name if a.family_of_origin else None,
                created_at=a.created_at,
            )
        )
    return result


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
        activity_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    activity = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Only allow parents to delete their own family's activities
    if current_user.family_id != activity.family_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this activity")

    db.delete(activity)
    db.commit()


# Add this endpoint after the read_activities_for_family route and before the parameterized routes

@router.get("/{family_id}/recent", response_model=list[activity_schema.ActivityOut])
def read_recent_activities_for_family(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    if current_user.role == RoleEnum.church_pastor:
        pass
    elif current_user.role in [RoleEnum.mere, RoleEnum.pere, RoleEnum.other, RoleEnum.admin]:
        if current_user.family_id != family_id:
            raise HTTPException(status_code=403, detail="Not authorized to view activities for this family.")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions to access family activities.")

    # Build base query with joinedload to include family name
    query = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.family_id == family_id)

    # Order by date descending and limit to 4
    query = query.order_by(_coalesced_start_date_col().desc()).limit(4)

    # Get activities and convert to Pydantic models
    activities = query.all()
    _maybe_promote_planned_to_ongoing(db, activities)
    return crud_activity.convert_activities_to_out(activities)