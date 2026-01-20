from typing import Any, List
from sqlalchemy.orm import Session, joinedload
from app.models.family_activity import Activity
from app.schemas.family_activity import ActivityCreate, ActivityOut
from app.utils.logging_decorator import log_create, log_view


def _activity_to_dict(activity: Activity) -> dict:
    """
    Helper function to convert SQLAlchemy Activity model to a dictionary
    that can be used to create a Pydantic model, avoiding SQLAlchemy internal attributes.
    """
    return {
        'id': activity.id,
        'family_id': activity.family_id,
        'family_name': activity.family.name if activity.family else "Unknown",
        'date': activity.date,
        'start_date': activity.start_date,
        'end_date': activity.end_date,
        'start_time': activity.start_time,
        'end_time': activity.end_time,
        'status': activity.status,
        'category': activity.category,
        'type': activity.type,
        'description': activity.description,
        'location': activity.location,
        'platform': activity.platform,
        'days': activity.days,
        'preachers': activity.preachers,
        'speakers': activity.speakers,
        'budget': activity.budget,
        'logistics': activity.logistics,
        'is_recurring_monthly': bool(activity.is_recurring_monthly) if activity.is_recurring_monthly is not None else None,
        'created_at': activity.created_at,
        'updated_at': activity.updated_at,
    }


@log_create("family_activities", "Created new family activity")
def create_activity(db: Session, activity: ActivityCreate):
    db_activity = Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)

    # Create the check-in session immediately so the QR can be used later.
    # Import locally to avoid circular imports.
    from app.controllers.activity_checkin import upsert_checkin_session
    upsert_checkin_session(db, db_activity)

    # Get the activity with family relationship loaded
    activity_with_family = db.query(Activity).options(joinedload(Activity.family)).filter(
        Activity.id == db_activity.id).first()

    # Convert to Pydantic model with family_name populated
    activity_dict = _activity_to_dict(activity_with_family)
    return ActivityOut(**activity_dict)


@log_view("family_activities", "Viewed family activities")
def get_activities_by_family(db: Session, family_id: int) -> List[ActivityOut]:
    activities = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.family_id == family_id).all()
    return convert_activities_to_out(activities)


@log_view("family_activities", "Viewed activity details")
def get_activity_by_id(db: Session, activity_id: int) -> ActivityOut | None:
    activity = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.id == activity_id).first()

    if not activity:
        return None

    # Convert to Pydantic model with family_name populated
    activity_dict = _activity_to_dict(activity)
    return ActivityOut(**activity_dict)


def convert_activities_to_out(activities: List[Activity]) -> List[ActivityOut]:
    """Helper function to convert SQLAlchemy models to Pydantic models with family_name"""
    result = []
    for activity in activities:
        activity_dict = _activity_to_dict(activity)
        result.append(ActivityOut(**activity_dict))
    
    return result