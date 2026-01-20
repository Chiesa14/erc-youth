from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.anti_drugs_unit import AntiDrugsActivity, AntiDrugsTestimony, AntiDrugsOutreachPlan
from app.schemas.anti_drugs_unit import (
    AntiDrugsActivityCreate,
    AntiDrugsActivityUpdate,
    AntiDrugsTestimonyCreate,
    AntiDrugsTestimonyUpdate,
    AntiDrugsOutreachPlanCreate,
    AntiDrugsOutreachPlanUpdate,
)


def list_activities(db: Session, frequency=None):
    query = db.query(AntiDrugsActivity)
    if frequency:
        query = query.filter(AntiDrugsActivity.frequency == frequency)
    return query.order_by(AntiDrugsActivity.id.desc()).all()


def create_activity(db: Session, payload: AntiDrugsActivityCreate):
    item = AntiDrugsActivity(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_activity(db: Session, activity_id: int, payload: AntiDrugsActivityUpdate):
    item = db.query(AntiDrugsActivity).filter(AntiDrugsActivity.id == activity_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_activity(db: Session, activity_id: int) -> None:
    item = db.query(AntiDrugsActivity).filter(AntiDrugsActivity.id == activity_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(item)
    db.commit()


def list_testimonies(db: Session):
    return db.query(AntiDrugsTestimony).order_by(AntiDrugsTestimony.id.desc()).all()


def create_testimony(db: Session, payload: AntiDrugsTestimonyCreate):
    item = AntiDrugsTestimony(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_testimony(db: Session, testimony_id: int, payload: AntiDrugsTestimonyUpdate):
    item = db.query(AntiDrugsTestimony).filter(AntiDrugsTestimony.id == testimony_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Testimony not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_testimony(db: Session, testimony_id: int) -> None:
    item = db.query(AntiDrugsTestimony).filter(AntiDrugsTestimony.id == testimony_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Testimony not found")
    db.delete(item)
    db.commit()


def list_outreach_plans(db: Session):
    return db.query(AntiDrugsOutreachPlan).order_by(AntiDrugsOutreachPlan.id.desc()).all()


def create_outreach_plan(db: Session, payload: AntiDrugsOutreachPlanCreate):
    item = AntiDrugsOutreachPlan(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_outreach_plan(db: Session, plan_id: int, payload: AntiDrugsOutreachPlanUpdate):
    item = db.query(AntiDrugsOutreachPlan).filter(AntiDrugsOutreachPlan.id == plan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Outreach plan not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_outreach_plan(db: Session, plan_id: int) -> None:
    item = db.query(AntiDrugsOutreachPlan).filter(AntiDrugsOutreachPlan.id == plan_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Outreach plan not found")
    db.delete(item)
    db.commit()
