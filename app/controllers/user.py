from sqlalchemy.orm import Session
from typing import List, Any

from app.models.family import Family
from app.models.user import User
from app.schemas.user import UserCreate, RoleEnum, UserUpdate, AdminUserUpdate
from app.schemas.user import FamilyCategoryEnum
from app.core.security import get_password_hash
from app.utils.timestamps import to_iso_format, add_timestamps_to_dict
from app.utils.logging_decorator import log_create, log_update, log_delete
from datetime import datetime
from app.models.user_invitation import UserInvitation

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
    if not user.password:
        raise ValueError("Password is required")

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
        family_id=family_id
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_or_update_user_invitation(db: Session, user_id: int, temp_password_hash: str) -> UserInvitation:
    invitation = db.query(UserInvitation).filter(UserInvitation.user_id == user_id).first()
    if invitation:
        invitation.temp_password = temp_password_hash
        invitation.is_activated = False
        invitation.activated_at = None
        invitation.created_at = datetime.utcnow()
    else:
        invitation = UserInvitation(user_id=user_id, temp_password=temp_password_hash)
        db.add(invitation)

    db.commit()
    db.refresh(invitation)
    return invitation


def verify_user_temp_password(db: Session, user_id: int, temp_password_plain: str) -> bool:
    invitation = db.query(UserInvitation).filter(UserInvitation.user_id == user_id).first()
    if not invitation or invitation.is_activated:
        return False

    # Stored temp_password is a hashed value (same as FamilyMemberInvitation)
    from app.core import security

    return security.verify_password(temp_password_plain, invitation.temp_password)


def mark_user_invitation_activated(db: Session, user_id: int) -> None:
    invitation = db.query(UserInvitation).filter(UserInvitation.user_id == user_id).first()
    if not invitation:
        return
    invitation.is_activated = True
    invitation.activated_at = datetime.utcnow()
    db.commit()


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


