from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import RoleEnum
from app.models.family_role import FamilyRole

from app.controllers import organization as crud
from app.schemas.organization import (
    OrganizationPositionOut,
    OrganizationPositionCreate,
    OrganizationPositionUpdate,
    SmallCommitteeOut,
    SmallCommitteeCreate,
    SmallCommitteeUpdate,
)


router = APIRouter(tags=["Organization"])


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


@router.get("/positions", response_model=list[OrganizationPositionOut])
def list_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_positions(db)


@router.post("/positions", response_model=OrganizationPositionOut, status_code=status.HTTP_201_CREATED)
def create_position(
    payload: OrganizationPositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_position(db, payload)


@router.put("/positions/{position_id}", response_model=OrganizationPositionOut)
def update_position(
    position_id: int,
    payload: OrganizationPositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_position(db, position_id, payload)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_position(db, position_id)


@router.get("/small-committees", response_model=list[SmallCommitteeOut])
def list_small_committees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_small_committees(db)


@router.post("/small-committees", response_model=SmallCommitteeOut, status_code=status.HTTP_201_CREATED)
def create_small_committee(
    payload: SmallCommitteeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_small_committee(db, payload)


@router.put("/small-committees/{committee_id}", response_model=SmallCommitteeOut)
def update_small_committee(
    committee_id: int,
    payload: SmallCommitteeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_small_committee(db, committee_id, payload)


@router.delete("/small-committees/{committee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_small_committee(
    committee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_small_committee(db, committee_id)
