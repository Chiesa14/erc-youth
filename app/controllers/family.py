from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.db.session import SessionLocal
from app.models.family import Family
from app.models.user import User
from app.models.family_member import FamilyMember
from app.models.family_activity import Activity
from app.schemas.family import FamilyResponse, FamilyCreate, FamilyUpdate, FamilyMemberCreate, ActivityCreate, \
    ActivityResponse
from app.schemas.user import RoleEnum, GenderEnum
from app.utils.timestamps import to_iso_format, add_timestamps_to_dict
from app.utils.logging_decorator import log_create, log_update, log_delete, log_view


def _resolve_leader_member(db: Session, family_id: int, user: User | None) -> FamilyMember | None:
    if not user:
        return None

    if user.email:
        m = (
            db.query(FamilyMember)
            .filter(
                FamilyMember.family_id == family_id,
                FamilyMember.email == user.email,
            )
            .first()
        )
        if m:
            return m

    if user.phone:
        m = (
            db.query(FamilyMember)
            .filter(
                FamilyMember.family_id == family_id,
                FamilyMember.phone == user.phone,
            )
            .first()
        )
        if m:
            return m

    if user.full_name:
        m = (
            db.query(FamilyMember)
            .filter(
                FamilyMember.family_id == family_id,
                FamilyMember.name == user.full_name,
            )
            .first()
        )
        if m:
            return m

    return None


@log_view("families", "Viewed all families")
def get_all_families(db: Session) -> List[FamilyResponse]:
    last_activity_subquery = (
        db.query(
            Activity.family_id,
            func.max(func.coalesce(Activity.end_date, Activity.date)).label("last_activity_date"),
        )
        .group_by(Activity.family_id)
        .subquery()
    )

    families = (
        db.query(Family)
        .outerjoin(FamilyMember, Family.members)
        .outerjoin(last_activity_subquery, Family.id == last_activity_subquery.c.family_id)
        .all()
    )

    result = []
    for family in families:
        # Query users table to find pere (father) and mere (mother)
        pere_user = (
            db.query(User)
            .filter(
                User.family_id == family.id,
                User.role == RoleEnum.pere,
                User.gender == GenderEnum.male
            )
            .first()
        )
        mere_user = (
            db.query(User)
            .filter(
                User.family_id == family.id,
                User.role == RoleEnum.mere,
                User.gender == GenderEnum.female
            )
            .first()
        )

        pere = pere_user.full_name if pere_user else None
        mere = mere_user.full_name if mere_user else None
        pere_member = _resolve_leader_member(db, family.id, pere_user)
        mere_member = _resolve_leader_member(db, family.id, mere_user)

        if pere_member and pere_member.name:
            pere = pere_member.name
        if mere_member and mere_member.name:
            mere = mere_member.name

        pere_pic = (pere_member.profile_photo if pere_member else None) or (
            pere_user.profile_pic if pere_user else None
        )
        mere_pic = (mere_member.profile_photo if mere_member else None) or (
            mere_user.profile_pic if mere_user else None
        )

        members = [member.name for member in family.members]
        activities = [
            ActivityResponse(
                id=activity.id,
                date=activity.start_date or activity.date,
                status=activity.status,
                category=activity.category,
                type=activity.type,
                description=activity.description
            )
            for activity in db.query(Activity)
            .filter(Activity.family_id == family.id)
            .all()
        ]

        last_activity_date = (
            db.query(last_activity_subquery.c.last_activity_date)
            .filter(last_activity_subquery.c.family_id == family.id)
            .scalar()
        )

        family_data = FamilyResponse(
            id=family.id,
            name=family.name,
            category=family.category,
            cover_photo=family.cover_photo,
            pere=pere,
            mere=mere,
            pere_pic=pere_pic,
            mere_pic=mere_pic,
            members=members,
            activities=activities,
            last_activity_date=last_activity_date
        )
        result.append(family_data)

    return result


@log_view("families", "Viewed family details")
def get_family_by_id(db: Session, family_id: int) -> FamilyResponse:
    last_activity_subquery = (
        db.query(
            Activity.family_id,
            func.max(func.coalesce(Activity.end_date, Activity.date)).label("last_activity_date"),
        )
        .group_by(Activity.family_id)
        .subquery()
    )

    family = (
        db.query(Family)
        .outerjoin(FamilyMember, Family.members)
        .outerjoin(last_activity_subquery, Family.id == last_activity_subquery.c.family_id)
        .filter(Family.id == family_id)
        .first()
    )

    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    # Query users table to find pere (father) and mere (mother)
    pere_user = (
        db.query(User)
        .filter(
            User.family_id == family.id,
            User.role == RoleEnum.pere,
            User.gender == GenderEnum.male
        )
        .first()
    )
    mere_user = (
        db.query(User)
        .filter(
            User.family_id == family.id,
            User.role == RoleEnum.mere,
            User.gender == GenderEnum.female
        )
        .first()
    )

    pere = pere_user.full_name if pere_user else None
    mere = mere_user.full_name if mere_user else None

    pere_member = _resolve_leader_member(db, family.id, pere_user)
    mere_member = _resolve_leader_member(db, family.id, mere_user)

    if pere_member and pere_member.name:
        pere = pere_member.name
    if mere_member and mere_member.name:
        mere = mere_member.name

    pere_pic = (pere_member.profile_photo if pere_member else None) or (
        pere_user.profile_pic if pere_user else None
    )
    mere_pic = (mere_member.profile_photo if mere_member else None) or (
        mere_user.profile_pic if mere_user else None
    )

    members = [member.name for member in family.members]
    activities = [
        ActivityResponse(
            id=activity.id,
            date=activity.start_date or activity.date,
            status=activity.status,
            category=activity.category,
            type=activity.type,
            description=activity.description
        )
        for activity in db.query(Activity)
        .filter(Activity.family_id == family.id)
        .all()
    ]

    last_activity_date = (
        db.query(last_activity_subquery.c.last_activity_date)
        .filter(last_activity_subquery.c.family_id == family.id)
        .scalar()
    )

    return FamilyResponse(
        id=family.id,
        name=family.name,
        category=family.category,
        cover_photo=family.cover_photo,
        pere=pere,
        mere=mere,
        pere_pic=pere_pic,
        mere_pic=mere_pic,
        members=members,
        activities=activities,
        last_activity_date=last_activity_date
    )


@log_create("families", "Created family")
def create_family(db: Session, family: FamilyCreate) -> FamilyResponse:
    # Check if a family with the same category and name already exists
    existing_family = db.query(Family).filter(
        Family.category == family.category,
        Family.name == family.name
    ).first()

    if existing_family:
        raise HTTPException(status_code=400,
                            detail=f"Family with name '{family.name}' and category '{family.category}' already exists")

    # Create new family if no duplicate is found
    db_family = Family(category=family.category, name=family.name)
    # created_at and updated_at will be automatically set by the middleware
    db.add(db_family)
    db.commit()
    db.refresh(db_family)
    return get_family_by_id(db, db_family.id)

@log_update("families", "Updated family")
def update_family(db: Session, family_id: int, family: FamilyUpdate) -> FamilyResponse:
    db_family = db.query(Family).filter(Family.id == family_id).first()
    if not db_family:
        raise HTTPException(status_code=404, detail="Family not found")

    update_data = family.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_family, key, value)

    # updated_at will be automatically set by the middleware
    db.commit()
    db.refresh(db_family)
    return get_family_by_id(db, db_family.id)

@log_delete("families", "Deleted family")
def delete_family(db: Session, family_id: int):
    db_family = db.query(Family).filter(Family.id == family_id).first()
    if not db_family:
        raise HTTPException(status_code=404, detail="Family not found")

    db.delete(db_family)
    db.commit()
    return {"message": "Family deleted successfully"}

