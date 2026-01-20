from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import RoleEnum
from app.models.family_role import FamilyRole

from app.controllers import anti_drugs_unit as crud
from app.schemas.anti_drugs_unit import (
    AntiDrugsActivityOut,
    AntiDrugsActivityCreate,
    AntiDrugsActivityUpdate,
    AntiDrugsTestimonyOut,
    AntiDrugsTestimonyCreate,
    AntiDrugsTestimonyUpdate,
    AntiDrugsOutreachPlanOut,
    AntiDrugsOutreachPlanCreate,
    AntiDrugsOutreachPlanUpdate,
    ActivityFrequencyEnum,
)


router = APIRouter(tags=["Anti-Drugs Unit"])


def require_youth_committee(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role in {RoleEnum.admin, RoleEnum.church_pastor}:
        return current_user

    if current_user.role != RoleEnum.other:
        raise HTTPException(status_code=403, detail="Access denied")

    if not current_user.family_role_id:
        raise HTTPException(status_code=403, detail="Access denied")

    family_role = (
        db.query(FamilyRole)
        .filter(FamilyRole.id == current_user.family_role_id)
        .first()
    )
    if not family_role:
        raise HTTPException(status_code=403, detail="Access denied")

    role_name = (family_role.name or "").strip().lower()
    if role_name not in {"youth leader", "youth committee"}:
        raise HTTPException(status_code=403, detail="Access denied")

    return current_user


@router.get("/activities", response_model=list[AntiDrugsActivityOut])
def list_anti_drugs_activities(
    frequency: Optional[ActivityFrequencyEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_activities(db, frequency=frequency)


@router.post("/activities", response_model=AntiDrugsActivityOut, status_code=status.HTTP_201_CREATED)
def create_anti_drugs_activity(
    payload: AntiDrugsActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_activity(db, payload)


@router.put("/activities/{activity_id}", response_model=AntiDrugsActivityOut)
def update_anti_drugs_activity(
    activity_id: int,
    payload: AntiDrugsActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_activity(db, activity_id, payload)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anti_drugs_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_activity(db, activity_id)


@router.get("/testimonies", response_model=list[AntiDrugsTestimonyOut])
def list_anti_drugs_testimonies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_testimonies(db)


@router.post("/testimonies", response_model=AntiDrugsTestimonyOut, status_code=status.HTTP_201_CREATED)
def create_anti_drugs_testimony(
    payload: AntiDrugsTestimonyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_testimony(db, payload)


@router.put("/testimonies/{testimony_id}", response_model=AntiDrugsTestimonyOut)
def update_anti_drugs_testimony(
    testimony_id: int,
    payload: AntiDrugsTestimonyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_testimony(db, testimony_id, payload)


@router.delete("/testimonies/{testimony_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anti_drugs_testimony(
    testimony_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_testimony(db, testimony_id)


@router.get("/outreach-plans", response_model=list[AntiDrugsOutreachPlanOut])
def list_outreach_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_outreach_plans(db)


@router.post("/outreach-plans", response_model=AntiDrugsOutreachPlanOut, status_code=status.HTTP_201_CREATED)
def create_outreach_plan(
    payload: AntiDrugsOutreachPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_outreach_plan(db, payload)


@router.put("/outreach-plans/{plan_id}", response_model=AntiDrugsOutreachPlanOut)
def update_outreach_plan(
    plan_id: int,
    payload: AntiDrugsOutreachPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_outreach_plan(db, plan_id, payload)


@router.delete("/outreach-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_outreach_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_outreach_plan(db, plan_id)
