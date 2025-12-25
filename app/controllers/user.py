from sqlalchemy.orm import Session
from typing import List, Any

from app.models.family import Family
from app.models.user import User
from app.schemas.user import UserCreate, RoleEnum, UserUpdate, AdminUserUpdate
from app.schemas.user import FamilyCategoryEnum
from app.core.security import get_password_hash
from app.utils.timestamps import to_iso_format, add_timestamps_to_dict
from app.utils.logging_decorator import log_create, log_update, log_delete
import random


def generate_unique_access_code(db: Session) -> str:
    while True:
        code = f"{random.randint(1000, 9999)}"
        if not db.query(User).filter(User.access_code == code).first():
            return code


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_or_create_family(db: Session, category: str, name: str) -> Family:
    family = db.query(Family).filter_by(category=category, name=name).first()
    if not family:
        family = Family(category=category, name=name)
        db.add(family)
        db.commit()
        db.refresh(family)
    return family


def get_family_by_id_or_400(db: Session, family_id: int) -> Family:
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise ValueError(f"Family with id '{family_id}' not found")
    return family


@log_create("user", "Created new user account")
def create_user(db: Session, user: UserCreate):
    access_code = None

    if user.role != RoleEnum.admin:
        access_code = generate_unique_access_code(db)
        hashed_pw = get_password_hash(access_code)
    else:
        hashed_pw = get_password_hash(user.password)

    family_id = None
    family_category = user.family_category
    family_name = user.family_name
    if user.family_id is not None:
        family = get_family_by_id_or_400(db, user.family_id)
        family_id = family.id

        family_name = family.name
        try:
            family_category = FamilyCategoryEnum(family.category)
        except Exception:
            family_category = None

    db_user = User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed_pw,
        gender=user.gender,
        phone=user.phone,
        family_category=family_category,
        family_name=family_name,
        role=user.role,
        other=user.other,
        profile_pic=user.profile_pic,
        access_code=access_code,
        family_id=family_id
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@log_update("user", "Updated user profile")
def update_user_profile(db: Session, user: User, updates: UserUpdate) -> type[User]:
    # Get the user from the current session using the user's ID
    db_user = db.query(User).filter(User.id == user.id).first()

    if not db_user:
        raise ValueError("User not found")

    # Apply updates
    if updates.biography is not None:
        db_user.biography = updates.biography
    if updates.other is not None:
        db_user.other = updates.other
    if updates.profile_pic is not None:
        db_user.profile_pic = updates.profile_pic

    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(db_user)
    return db_user


@log_update("user", "Reset user access code")
def reset_user_access_code(db: Session, user: User) -> tuple[User, str]:
    new_code = generate_unique_access_code(db)
    user.access_code = new_code
    user.hashed_password = get_password_hash(new_code)
    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(user)
    return user, new_code


@log_update("user", "Changed user password")
def update_user_password(db: Session, user: User, new_password: str) -> User:
    user.hashed_password = get_password_hash(new_password)
    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(user)
    return user


def get_all_users(db: Session) -> list[type[User]]:
    """
    Retrieve all users from the database.
    
    Args:
        db: Database session
        
    Returns:
        List of all users
    """
    return db.query(User).all()


@log_delete("user", "Deleted user account")
def delete_user(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    db.delete(user)
    db.commit()


@log_update("user", "Admin updated user information")
def admin_update_user(db: Session, user_id: int, updates: AdminUserUpdate) -> type[User]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise ValueError("User not found")

    # Update only provided fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(db_user, field, value)

    # Handle family relation via family_id (explicit link; no implicit creation)
    if 'family_id' in updates.dict(exclude_unset=True):
        if updates.family_id is None:
            db_user.family_id = None
            db_user.family_name = None
            db_user.family_category = None
        else:
            family = get_family_by_id_or_400(db, updates.family_id)
            db_user.family_id = family.id
            db_user.family_name = family.name
            try:
                db_user.family_category = FamilyCategoryEnum(family.category)
            except Exception:
                db_user.family_category = None

    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(db_user)
    return db_user


