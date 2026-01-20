from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.worship_team import WorshipTeamActivity
from app.schemas.worship_team import WorshipTeamActivityCreate, WorshipTeamActivityUpdate


def list_activities(db: Session, frequency=None):
    query = db.query(WorshipTeamActivity)
    if frequency:
        query = query.filter(WorshipTeamActivity.frequency == frequency)
    return query.order_by(WorshipTeamActivity.id.desc()).all()


def create_activity(db: Session, payload: WorshipTeamActivityCreate):
    item = WorshipTeamActivity(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_activity(db: Session, activity_id: int, payload: WorshipTeamActivityUpdate):
    item = db.query(WorshipTeamActivity).filter(WorshipTeamActivity.id == activity_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_activity(db: Session, activity_id: int) -> None:
    item = db.query(WorshipTeamActivity).filter(WorshipTeamActivity.id == activity_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(item)
    db.commit()
