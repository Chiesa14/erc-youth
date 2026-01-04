from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_active_user
from app.models.family_role import FamilyRole
from app.models.user import User
from app.schemas.user import RoleEnum
from app.schemas.bcc import (
    BccClassCompletionCreate,
    BccClassCompletionOut,
    BccMemberProgressOut,
    BccIncompleteMemberOut,
    BccFamilyCompletionOut,
)
import app.controllers.bcc as bcc_controller


router = APIRouter(tags=["BCC"])


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


@router.get("/members/{member_id}/progress", response_model=BccMemberProgressOut)
def get_member_progress(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    member = bcc_controller.get_member_with_bcc(db, member_id)

    can_view = False
    if current_user.role in {RoleEnum.admin, RoleEnum.church_pastor}:
        can_view = True
    elif current_user.role in {RoleEnum.pere, RoleEnum.mere, RoleEnum.other} and current_user.family_id:
        can_view = current_user.family_id == member.family_id

    if not can_view:
        raise HTTPException(status_code=403, detail="Access denied")

    completed, missing, is_complete, completion_percent = bcc_controller.compute_member_progress(member)

    return BccMemberProgressOut(
        member_id=member.id,
        member_name=member.name,
        family_id=member.family_id,
        completed_classes=completed,
        missing_classes=missing,
        is_complete=is_complete,
        completion_percent=completion_percent,
    )


@router.post(
    "/members/{member_id}/completions",
    response_model=BccClassCompletionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_member_completion(
    member_id: int,
    payload: BccClassCompletionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    completion = bcc_controller.record_class_completion(
        db,
        member_id=member_id,
        class_number=payload.class_number,
        recorded_by=current_user,
    )
    return BccClassCompletionOut.model_validate(completion)


@router.get("/incomplete", response_model=list[BccIncompleteMemberOut])
def list_incomplete(
    family_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_youth_committee),
):
    rows = bcc_controller.list_incomplete_members(db, family_id=family_id)
    return [BccIncompleteMemberOut(**row) for row in rows]


@router.get("/families/{family_id}/status", response_model=BccFamilyCompletionOut)
def get_family_status(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    can_view = False
    if current_user.role in {RoleEnum.admin, RoleEnum.church_pastor}:
        can_view = True
    elif current_user.family_id and current_user.family_id == family_id and current_user.role in {
        RoleEnum.pere,
        RoleEnum.mere,
        RoleEnum.other,
    }:
        can_view = True
    else:
        try:
            require_youth_committee(db=db, current_user=current_user)
            can_view = True
        except HTTPException:
            can_view = False

    if not can_view:
        raise HTTPException(status_code=403, detail="Access denied")

    is_complete, incomplete_members = bcc_controller.get_family_completion_status(
        db,
        family_id=family_id,
    )
    return BccFamilyCompletionOut(
        family_id=family_id,
        is_complete=is_complete,
        incomplete_members=[BccMemberProgressOut(**m) for m in incomplete_members],
    )
