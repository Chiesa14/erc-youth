from sqlalchemy.orm import Session
from typing import List, Any

from app.models.family import Family
from app.models.user import User
from app.schemas.user import UserCreate, RoleEnum, UserUpdate, AdminUserUpdate
from app.core.security import get_password_hash
from app.utils.timestamps import to_iso_format, add_timestamps_to_dict
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


def create_user(db: Session, user: UserCreate):
    access_code = None

    if user.role != RoleEnum.admin:
        access_code = generate_unique_access_code(db)
        hashed_pw = get_password_hash(access_code)
    else:
        hashed_pw = get_password_hash(user.password)

    family_id = None
    if user.family_category is not None and user.family_name is not None:
        family = get_or_create_family(db, user.family_category.value, user.family_name)
        family_id = family.id

    db_user = User(
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed_pw,
        gender=user.gender,
        phone=user.phone,
        family_category=user.family_category,
        family_name=user.family_name,
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

def reset_user_access_code(db: Session, user: User) -> tuple[User, str]:
    new_code = generate_unique_access_code(db)
    user.access_code = new_code
    user.hashed_password = get_password_hash(new_code)
    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(user)
    return user, new_code

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


def delete_user(db: Session, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    db.delete(user)
    db.commit()


def admin_update_user(db: Session, user_id: int, updates: AdminUserUpdate) -> type[User]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise ValueError("User not found")

    # Update only provided fields
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(db_user, field, value)

    # Handle family relation if both category and name are updated
    if ('family_category' in updates.dict(exclude_unset=True)
        and 'family_name' in updates.dict(exclude_unset=True)):
        family = get_or_create_family(
            db,
            updates.family_category.value,
            updates.family_name
        )
        db_user.family_id = family.id

    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(db_user)
    return db_user


