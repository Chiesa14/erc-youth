from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import app.controllers.user as crud_user
import app.schemas.user as user_schema
from app.db.session import get_db
from app.core.security import get_current_active_user, get_current_user
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import RoleEnum
from app.services.email_service import EmailService
from app.utils.timestamps import (
    parse_timestamp_filters,
    apply_timestamp_filters,
    apply_timestamp_sorting,
    TimestampQueryParams
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])

@router.post("/", response_model=user_schema.UserOut, status_code=status.HTTP_201_CREATED)
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

    try:
        email_service = EmailService()
        temp_password: str | None = None

        # If admin didn't provide a password, create a secure temporary password
        if not user.password:
            temp_password = email_service.generate_temporary_password()
            user = user.model_copy(update={"password": temp_password})

        created_user = crud_user.create_user(db, user)

        # If we generated a temporary password, create/update invitation and email user
        if temp_password:
            crud_user.create_or_update_user_invitation(
                db,
                user_id=created_user.id,
                temp_password_hash=get_password_hash(temp_password),
            )

            email_sent = email_service.send_user_invitation_email(
                to_email=created_user.email,
                user_name=created_user.full_name,
                temp_password=temp_password,
                user_id=created_user.id,
            )

            if not email_sent:
                logger.warning(f"Failed to send user invitation email to {created_user.email}")

        return created_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/activate", response_model=user_schema.UserActivationResponse)
def activate_user_account(
    request: user_schema.UserActivationRequest,
    db: Session = Depends(get_db),
):
    if not crud_user.verify_user_temp_password(db, request.user_id, request.temp_password):
        raise HTTPException(status_code=400, detail="Invalid temporary password or invitation already used.")

    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    crud_user.update_user_password(db, user, request.new_password)
    crud_user.mark_user_invitation_activated(db, request.user_id)

    return user_schema.UserActivationResponse(message="Account activated successfully", user_id=request.user_id)


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


@router.post("/reset-password/{user_id}", response_model=user_schema.PasswordResetResponse)
def admin_reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can reset passwords.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    email_service = EmailService()
    temp_password = email_service.generate_temporary_password()

    # Set the new password immediately (user can still change it via activation link)
    crud_user.update_user_password(db, user, temp_password)

    # Create/refresh invitation so activation link works and is marked not activated
    crud_user.create_or_update_user_invitation(
        db,
        user_id=user.id,
        temp_password_hash=get_password_hash(temp_password),
    )

    email_sent = email_service.send_user_invitation_email(
        to_email=user.email,
        user_name=user.full_name,
        temp_password=temp_password,
        user_id=user.id,
    )

    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send reset password email.")

    return user_schema.PasswordResetResponse(
        message="Password reset email sent successfully",
        user_id=user.id,
    )


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
    logger.debug(f"User role: {current_user.role.value}")
    if current_user.role not in {RoleEnum.admin, RoleEnum.pere, RoleEnum.mere}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins,pere or mere can retrieve all users."
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
        message = str(e)
        status_code = 404 if message == "User not found" else 400
        raise HTTPException(status_code=status_code, detail=message)

    return updated_user
