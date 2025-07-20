from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.controllers import family_member as crud_member
from app.db.session import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_parent
from app.models.user import User
from app.schemas.family_member import (
    FamilyMemberCreate,
    FamilyMemberOut,
    FamilyMemberUpdate,
    GrantAccessRequest,
    DelegatedAccessOut
)

router = APIRouter(tags=["Family Members"])


# ========================
# 🚪 Access Management First (Specific routes go before dynamic ones!)
# ========================

@router.post("/access/grant", status_code=status.HTTP_204_NO_CONTENT)
def grant_access(
    request: GrantAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    crud_member.grant_permissions_to_member(db, current_user.family_id, request, current_user)


@router.get("/access", response_model=list[DelegatedAccessOut])
def list_access_grants(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    return crud_member.get_members_with_permissions(db, current_user.family_id)


@router.post("/access/update", status_code=status.HTTP_204_NO_CONTENT)
def update_access(
    request: GrantAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    crud_member.update_member_permissions(db, current_user.family_id, request, current_user)


@router.delete("/access/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="No family assigned to user.")

    crud_member.revoke_member_permissions(db, current_user.family_id, member_id)


# ========================
# 👨‍👩‍👧 Family Member CRUD
# ========================

@router.post("/", response_model=FamilyMemberOut, status_code=status.HTTP_201_CREATED)
def create_member(
    member: FamilyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not assigned to any family.")

    member_data = member.model_copy(update={"family_id": current_user.family_id})
    db_member = crud_member.create_family_member(db, member_data)
    return FamilyMemberOut.model_validate(db_member)


@router.get("/", response_model=list[FamilyMemberOut])
def list_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User is not assigned to any family.")

    return crud_member.get_family_members_by_family_id(db, current_user.family_id)


@router.get("/{member_id}", response_model=FamilyMemberOut)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    member = crud_member.get_family_member_by_id(db, member_id)
    if not member or member.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    return member


@router.put("/{member_id}", response_model=FamilyMemberOut)
def update_member(
    member_id: int,
    updates: FamilyMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    member = crud_member.get_family_member_by_id(db, member_id)
    if not member or member.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    return crud_member.update_family_member(db, member_id, updates)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    require_parent(current_user)

    member = crud_member.get_family_member_by_id(db, member_id)
    if not member or member.family_id != current_user.family_id:
        raise HTTPException(status_code=404, detail="Family member not found.")

    if not crud_member.delete_family_member(db, member_id):
        raise HTTPException(status_code=500, detail="Failed to delete member.")
