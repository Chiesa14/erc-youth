from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import RoleEnum
from app.models.family_role import FamilyRole

from app.controllers import worship_team as crud
from app.schemas.worship_team import (
    WorshipTeamActivityOut,
    WorshipTeamActivityCreate,
    WorshipTeamActivityUpdate,
    WorshipTeamMemberOut,
    WorshipTeamMemberCreate,
    WorshipTeamMemberUpdate,
    WorshipTeamSongOut,
    WorshipTeamSongCreate,
    WorshipTeamSongUpdate,
    ActivityFrequencyEnum,
)


router = APIRouter(tags=["Worship Team"])


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


@router.get("/activities", response_model=list[WorshipTeamActivityOut])
def list_worship_team_activities(
    frequency: Optional[ActivityFrequencyEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_activities(db, frequency=frequency)


@router.post("/activities", response_model=WorshipTeamActivityOut, status_code=status.HTTP_201_CREATED)
def create_worship_team_activity(
    payload: WorshipTeamActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_activity(db, payload)


@router.put("/activities/{activity_id}", response_model=WorshipTeamActivityOut)
def update_worship_team_activity(
    activity_id: int,
    payload: WorshipTeamActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_activity(db, activity_id, payload)


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worship_team_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_activity(db, activity_id)


@router.get("/members", response_model=list[WorshipTeamMemberOut])
def list_worship_team_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_members(db)


@router.post("/members", response_model=WorshipTeamMemberOut, status_code=status.HTTP_201_CREATED)
def create_worship_team_member(
    payload: WorshipTeamMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_member(db, payload)


@router.put("/members/{member_id}", response_model=WorshipTeamMemberOut)
def update_worship_team_member(
    member_id: int,
    payload: WorshipTeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_member(db, member_id, payload)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worship_team_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_member(db, member_id)


@router.get("/songs", response_model=list[WorshipTeamSongOut])
def list_worship_team_songs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.list_songs(db)


@router.post("/songs", response_model=WorshipTeamSongOut, status_code=status.HTTP_201_CREATED)
def create_worship_team_song(
    payload: WorshipTeamSongCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.create_song(db, payload)


@router.put("/songs/{song_id}", response_model=WorshipTeamSongOut)
def update_worship_team_song(
    song_id: int,
    payload: WorshipTeamSongUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    return crud.update_song(db, song_id, payload)


@router.delete("/songs/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worship_team_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    crud.delete_song(db, song_id)
