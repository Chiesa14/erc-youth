from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.permissions import get_admin_user
from app.db.session import get_db
from app.schemas.family_role import FamilyRoleOut, FamilyRoleCreate, FamilyRoleUpdate
from app.controllers.family_role import (
    get_all_family_roles,
    create_family_role,
    update_family_role,
    delete_family_role,
)
from app.models.user import User


router = APIRouter()


@router.get("/", response_model=List[FamilyRoleOut])
def list_family_roles(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    return get_all_family_roles(db)


@router.post("/", response_model=FamilyRoleOut, status_code=status.HTTP_201_CREATED)
def create_family_role_route(
    role_in: FamilyRoleCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    try:
        return create_family_role(db, role_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{role_id}", response_model=FamilyRoleOut)
def update_family_role_route(
    role_id: int,
    role_in: FamilyRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    try:
        return update_family_role(db, role_id, role_in)
    except ValueError as e:
        message = str(e)
        status_code = 404 if message == "Role not found" else 400
        raise HTTPException(status_code=status_code, detail=message)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_family_role_route(
    role_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    try:
        delete_family_role(db, role_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
