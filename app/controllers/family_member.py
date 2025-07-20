from sqlalchemy.orm import Session, joinedload
from app.models.family_member import FamilyMember, FamilyMemberPermission
from app.models.user import User
from app.schemas.family_member import FamilyMemberUpdate, GrantAccessRequest, DelegatedAccessOut

from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.family_member import FamilyMember
from app.schemas.family_member import FamilyMemberCreate


def create_family_member(db: Session, member: FamilyMemberCreate) -> FamilyMember:
    existing_name = db.query(FamilyMember).filter(
        FamilyMember.name == member.name,
        FamilyMember.family_id == member.family_id
    ).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Member name already exists in the family.")

    # Phone is required and must be unique
    existing_phone = db.query(FamilyMember).filter(
        FamilyMember.phone == member.phone
    ).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone number already in use.")

    # Email is optional but must be unique if present
    if member.email:
        existing_email = db.query(FamilyMember).filter(
            FamilyMember.email == member.email
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already in use.")

    db_member = FamilyMember(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member



def get_family_members_by_family_id(db: Session, family_id: int) -> list[type[FamilyMember]]:
    return db.query(FamilyMember).filter(FamilyMember.family_id == family_id).all()


def get_family_member_by_id(db: Session, member_id: int) -> FamilyMember | None:
    return db.query(FamilyMember).filter(FamilyMember.id == member_id).first()


def update_family_member(
    db: Session, member_id: int, updates: FamilyMemberUpdate
) -> FamilyMember | None:
    db_member = get_family_member_by_id(db, member_id)
    if not db_member:
        return None

    update_data = updates.dict(exclude_unset=True)

    # Validate name + family_id uniqueness
    if "name" in update_data or "family_id" in update_data:
        new_name = update_data.get("name", db_member.name)
        new_family_id = update_data.get("family_id", db_member.family_id)
        existing = db.query(FamilyMember).filter(
            FamilyMember.name == new_name,
            FamilyMember.family_id == new_family_id,
            FamilyMember.id != member_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Another member with that name exists in this family.")

    # Validate phone uniqueness
    if "phone" in update_data:
        existing = db.query(FamilyMember).filter(
            FamilyMember.phone == update_data["phone"],
            FamilyMember.id != member_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Phone number already in use.")

    # Validate email uniqueness if provided
    if "email" in update_data and update_data["email"]:
        existing = db.query(FamilyMember).filter(
            FamilyMember.email == update_data["email"],
            FamilyMember.id != member_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use.")

    for key, value in update_data.items():
        setattr(db_member, key, value)

    db.commit()
    db.refresh(db_member)
    return db_member

def delete_family_member(db: Session, member_id: int) -> bool:
    db_member = get_family_member_by_id(db, member_id)
    if not db_member:
        return False

    db.delete(db_member)
    db.commit()
    return True



def grant_permissions_to_member(
    db: Session,
    family_id: int,
    request: GrantAccessRequest,
    current_user: User,  # ✅ new parameter for user validation
) -> None:
    # ✅ Ensure user is modifying their own family
    if current_user.family_id != family_id:
        raise HTTPException(status_code=403, detail="You do not have access to this family.")

    # ✅ Validate target member belongs to the same family
    member = db.query(FamilyMember).filter(
        FamilyMember.id == request.member_id,
        FamilyMember.family_id == family_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found in your family.")

    # ✅ Clear any existing permissions for this member
    db.query(FamilyMemberPermission).filter(
        FamilyMemberPermission.member_id == request.member_id
    ).delete()

    # ✅ Assign the new permissions
    for perm in request.permissions:
        db.add(FamilyMemberPermission(member_id=request.member_id, permission=perm))

    db.commit()


def get_members_with_permissions(db: Session, family_id: int) -> list[DelegatedAccessOut]:
    members = db.query(FamilyMember).options(joinedload(FamilyMember.permissions)) \
        .filter(FamilyMember.family_id == family_id).all()

    result = []
    for member in members:
        if member.permissions:
            result.append(DelegatedAccessOut(
                member_id=member.id,
                name=member.name,
                permissions=[perm.permission for perm in member.permissions]
            ))

    return result


def update_member_permissions(
    db: Session,
    family_id: int,
    request: GrantAccessRequest,
    current_user: User
):
    return grant_permissions_to_member(db, family_id, request, current_user)


def revoke_member_permissions(
    db: Session,
    family_id: int,
    member_id: int
):
    member = db.query(FamilyMember).filter(
        FamilyMember.id == member_id,
        FamilyMember.family_id == family_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Family member not found.")

    db.query(FamilyMemberPermission).filter(
        FamilyMemberPermission.member_id == member_id
    ).delete()

    db.commit()