from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.permissions import get_admin_user
from app.core.security import get_current_user
from app.db.session import get_db
from app.controllers.family import get_all_families,get_family_by_id,create_family,update_family,delete_family
from app.models.user import User
from app.models.family import Family

from app.schemas.family import FamilyResponse, FamilyCreate, FamilyUpdate
from app.utils.timestamps import (
    parse_timestamp_filters,
    apply_timestamp_filters,
    apply_timestamp_sorting
)

router = APIRouter()
@router.get("/", response_model=List[FamilyResponse])
def read_families(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    created_after: Optional[str] = Query(None, description="Filter families created after this timestamp (ISO 8601)"),
    created_before: Optional[str] = Query(None, description="Filter families created before this timestamp (ISO 8601)"),
    updated_after: Optional[str] = Query(None, description="Filter families updated after this timestamp (ISO 8601)"),
    updated_before: Optional[str] = Query(None, description="Filter families updated before this timestamp (ISO 8601)"),
    sort_by: Optional[str] = Query(None, description="Sort by timestamp field", enum=["created_at", "updated_at"]),
    sort_order: Optional[str] = Query("desc", description="Sort order", enum=["asc", "desc"]),
):
    try:
        # If no timestamp filters are provided, use the original function
        if not any([created_after, created_before, updated_after, updated_before, sort_by]):
            families = get_all_families(db)
            return families
        
        # Parse timestamp filters
        filters = parse_timestamp_filters(created_after, created_before, updated_after, updated_before)
        
        # Build query with filters and sorting
        query = db.query(Family)
        query = apply_timestamp_filters(query, Family, filters)
        query = apply_timestamp_sorting(query, Family, sort_by, sort_order)
        
        # Get filtered families and convert to response format
        filtered_families = query.all()
        
        # Convert to FamilyResponse format using the existing logic
        # This is a simplified version - in production you might want to optimize this
        family_responses = []
        for family in filtered_families:
            family_response = get_family_by_id(db, family.id)
            family_responses.append(family_response)
        
        return family_responses
        
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