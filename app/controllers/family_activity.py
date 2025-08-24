from typing import Any, List
from sqlalchemy.orm import Session, joinedload
from app.models.family_activity import Activity
from app.schemas.family_activity import ActivityCreate, ActivityOut
from app.utils.logging_decorator import log_create, log_view


@log_create("family_activities", "Created new family activity")
def create_activity(db: Session, activity: ActivityCreate):
    db_activity = Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)

    # Get the activity with family relationship loaded
    activity_with_family = db.query(Activity).options(joinedload(Activity.family)).filter(
        Activity.id == db_activity.id).first()

    # Convert to Pydantic model with family_name populated
    activity_dict = {
        **activity_with_family.__dict__,
        'family_name': activity_with_family.family.name if activity_with_family.family else "Unknown"
    }

    return ActivityOut(**activity_dict)


@log_view("family_activities", "Viewed family activities")
def get_activities_by_family(db: Session, family_id: int) -> List[ActivityOut]:
    activities = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.family_id == family_id).all()

    # Convert to Pydantic models with family_name populated
    result = []
    for activity in activities:
        activity_dict = {
            **activity.__dict__,
            'family_name': activity.family.name if activity.family else "Unknown"
        }
        result.append(ActivityOut(**activity_dict))

    return result


@log_view("family_activities", "Viewed activity details")
def get_activity_by_id(db: Session, activity_id: int) -> ActivityOut | None:
    activity = db.query(Activity).options(joinedload(Activity.family)).filter(Activity.id == activity_id).first()

    if not activity:
        return None

    # Convert to Pydantic model with family_name populated
    activity_dict = {
        **activity.__dict__,
        'family_name': activity.family.name if activity.family else "Unknown"
    }

    return ActivityOut(**activity_dict)


def convert_activities_to_out(activities: List[Activity]) -> List[ActivityOut]:
    """Helper function to convert SQLAlchemy models to Pydantic models with family_name"""
    result = []
    for activity in activities:
        activity_dict = {
            **activity.__dict__,
            'family_name': activity.family.name if activity.family else "Unknown"
        }
        result.append(ActivityOut(**activity_dict))

    return result