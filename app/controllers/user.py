from typing import Any

from fastapi import HTTPException
from pydantic.v1 import NoneStr
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.user import User
from app.schemas.user import UserCreate, RoleEnum, UserUpdate
from app.core.security import get_password_hash
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

    family = get_or_create_family(db, user.family_category.value, user.family_name)

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
        family_id=family.id
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

    db.commit()
    db.refresh(db_user)
    return db_user

def reset_user_access_code(db: Session, user: User) -> tuple[User, str]:
    new_code = generate_unique_access_code(db)
    user.access_code = new_code
    user.hashed_password = get_password_hash(new_code)
    db.commit()
    db.refresh(user)
    return user, new_code

def update_user_password(db: Session, user: User, new_password: str) -> User:
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    db.refresh(user)
    return user


def create_user_from_member_data(db: Session, member: FamilyMember, password: str) -> User:
    """Create user specifically from family member data"""

    # Generate access code for non-admin users
    access_code = generate_unique_access_code(db)
    hashed_pw = get_password_hash(password)

    # Get or create family (should already exist)
    family = db.query(Family).filter(Family.id == member.family_id).first()
    if not family:
        raise HTTPException(status_code=400, detail="Family not found.")

    db_user = User(
        full_name=member.name,
        email=member.email,
        hashed_password=hashed_pw,
        gender=member.gender,
        phone=member.phone,
        family_category=family.category,
        family_name=family.name,
        role=RoleEnum.other,  # Default role
        other=NoneStr,
        profile_pic=NoneStr,
        access_code=access_code,
        family_id=family.id
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user