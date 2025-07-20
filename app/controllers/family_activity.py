from sqlalchemy.orm import Session

from app.models.family_activity import Activity
from app.schemas.family_activity import ActivityCreate


def create_activity(db: Session, activity: ActivityCreate) -> Activity:
    db_activity = Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity

def get_activities_by_family(db: Session, family_id: int):
    return db.query(Activity).filter(Activity.family_id == family_id).all()

def get_activity_by_id(db: Session, activity_id: int):
    return db.query(Activity).filter(Activity.id == activity_id).first()
