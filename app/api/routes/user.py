from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import app.controllers.user as crud_user
import app.schemas.user as user_schema
from app.db.session import get_db
from app.core.security import get_current_active_user, get_current_user
from app.models.user import User
from app.utils.timestamps import (
    parse_timestamp_filters,
    apply_timestamp_filters,
    apply_timestamp_sorting,
    TimestampQueryParams
)

router = APIRouter(tags=["Users"])

@router.post("/", response_model=user_schema.UserOutWithCode, status_code=status.HTTP_201_CREATED)
def create_user(
    user: user_schema.UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create users.")

    db_user = crud_user.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    return crud_user.create_user(db, user)


@router.get("/me", response_model=user_schema.UserOut)
def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current user's profile using the bearer token"""
    return current_user


@router.put("/me", response_model=user_schema.UserOut)
def update_my_profile(
    updates: user_schema.UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_user = crud_user.update_user_profile(db=db, user=current_user, updates=updates)
    return updated_user


@router.put("/reset-access-code/{user_id}", response_model=user_schema.UserOutWithCode)
def admin_reset_access_code(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can reset access codes.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user, new_code = crud_user.reset_user_access_code(db, user)

    # Return user info + new access code (so admin can notify user)
    return user_schema.UserOutWithCode.from_orm(updated_user).copy(update={"access_code": new_code})


@router.put("/update-password/{user_id}", response_model=user_schema.UserOut)
def admin_update_user_password(
        user_id: int,
        password_update: user_schema.PasswordUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update passwords.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updated_user = crud_user.update_user_password(db, user, password_update.new_password)
    return updated_user


@router.get("/all", response_model=List[user_schema.UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    created_after: Optional[str] = Query(None, description="Filter users created after this timestamp (ISO 8601)"),
    created_before: Optional[str] = Query(None, description="Filter users created before this timestamp (ISO 8601)"),
    updated_after: Optional[str] = Query(None, description="Filter users updated after this timestamp (ISO 8601)"),
    updated_before: Optional[str] = Query(None, description="Filter users updated before this timestamp (ISO 8601)"),
    sort_by: Optional[str] = Query(None, description="Sort by timestamp field", enum=["created_at", "updated_at"]),
    sort_order: Optional[str] = Query("desc", description="Sort order", enum=["asc", "desc"]),
):
    """
    Retrieve all users in the system with timestamp filtering and sorting.
    Only accessible to admin users.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can retrieve all users."
        )
    
    # Parse timestamp filters
    filters = parse_timestamp_filters(created_after, created_before, updated_after, updated_before)
    
    # Build query with filters and sorting
    query = db.query(User)
    query = apply_timestamp_filters(query, User, filters)
    query = apply_timestamp_sorting(query, User, sort_by, sort_order)
    
    users = query.all()
    return users

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_route(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete users.")

    try:
        crud_user.delete_user(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None


@router.put("/update-user/{user_id}", response_model=user_schema.UserOut)
def admin_update_user_route(
    user_id: int,
    updates: user_schema.AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update user details.")

    try:
        updated_user = crud_user.admin_update_user(db, user_id, updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return updated_user
