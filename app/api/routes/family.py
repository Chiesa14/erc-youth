from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.permissions import get_admin_user
from app.core.security import get_current_user
from app.db.session import get_db
from app.controllers.family import get_all_families,get_family_by_id,create_family,update_family,delete_family
from app.models.user import User

from app.schemas.family import FamilyResponse, FamilyCreate, FamilyUpdate

router = APIRouter()
@router.get("/", response_model=List[FamilyResponse])
def read_families(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        families = get_all_families(db)
        return families
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching families: {str(e)}")

@router.get("/{family_id}", response_model=FamilyResponse)
def read_family(family_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        family = get_family_by_id(db, family_id)
        return family
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching family: {str(e)}")

@router.post("/", response_model=FamilyResponse)
def create_new_family(
    family: FamilyCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    try:
        return create_family(db, family)
    except HTTPException as e:
        raise e  # Re-raise HTTPException for duplicate family or other specific errors
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating family: {str(e)}")

@router.put("/{family_id}", response_model=FamilyResponse)
def update_existing_family(
    family_id: int,
    family: FamilyUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    try:
        return update_family(db, family_id, family)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating family: {str(e)}")

@router.delete("/{family_id}")
def delete_existing_family(
    family_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    try:
        return delete_family(db, family_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting family: {str(e)}")