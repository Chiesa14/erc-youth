from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import date
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
    if not activity.family_id:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User is not assigned to a family.")
        activity_data = activity.model_copy(update={"family_id": current_user.family_id})
    else:
        activity_data = activity
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

    # Apply date filters
    if activity_date:
        query = query.filter(Activity.date == activity_date)
    else:
        if date_from:
            query = query.filter(Activity.date >= date_from)
        if date_to:
            query = query.filter(Activity.date <= date_to)

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
            query = query.order_by(Activity.date.asc() if sort_order == "asc" else Activity.date.desc())
        elif sort_by == "family_id":
            query = query.order_by(Activity.family_id.asc() if sort_order == "asc" else Activity.family_id.desc())
        else:
            query = apply_timestamp_sorting(query, Activity, sort_by, sort_order)
    else:
        query = query.order_by(Activity.date.desc(), Activity.family_id.asc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Get activities and convert to Pydantic models
    activities = query.all()
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
        activity_date = activity.date

        # Count by status
        stats["by_status"][activity.status] += 1

        # Count by category
        stats["by_category"][activity.category] += 1

        # Count by family name
        family_name = activity.family.name if activity.family else "Unknown"
        stats["by_family"][family_name] += 1

        # This week activities
        if week_start <= activity_date <= week_end:
            stats["this_week"] += 1

        # Upcoming activities
        if activity_date > today:
            stats["upcoming"] += 1

        # Overdue activities
        if activity_date < today and activity.status in ["Planned", "Ongoing"]:
            stats["overdue"] += 1

    # Convert defaultdicts to regular dicts
    stats["by_status"] = dict(stats["by_status"])
    stats["by_category"] = dict(stats["by_category"])
    stats["by_family"] = dict(stats["by_family"])

    return stats


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

    # Apply date filters
    if activity_date:
        query = query.filter(Activity.date == activity_date)
    else:
        if date_from:
            query = query.filter(Activity.date >= date_from)
        if date_to:
            query = query.filter(Activity.date <= date_to)

    # Apply timestamp filters
    has_timestamp_filters = any([created_after, created_before, updated_after, updated_before])
    if has_timestamp_filters:
        filters = parse_timestamp_filters(created_after, created_before, updated_after, updated_before)
        query = apply_timestamp_filters(query, Activity, filters)

    # Apply sorting
    if sort_by:
        if sort_by == "date":
            query = query.order_by(Activity.date.asc() if sort_order == "asc" else Activity.date.desc())
        else:
            query = apply_timestamp_sorting(query, Activity, sort_by, sort_order)
    else:
        query = query.order_by(Activity.date.desc())

    # Get activities and convert to Pydantic models
    activities = query.all()
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

    for field, value in updated_data.dict(exclude_unset=True).items():
        setattr(activity, field, value)

    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(activity)

    # Refresh check-in window if date/time changed.
    crud_checkin.upsert_checkin_session(db, activity)

    # Convert to Pydantic model with family_name populated
    activity_dict = {
        **activity.__dict__,
        'family_name': activity.family.name if activity.family else "Unknown"
    }

    return activity_schema.ActivityOut(**activity_dict)


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
    query = query.order_by(Activity.date.desc()).limit(4)

    # Get activities and convert to Pydantic models
    activities = query.all()
    return crud_activity.convert_activities_to_out(activities)