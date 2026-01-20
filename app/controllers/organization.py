from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.organization import (
    OrganizationPosition,
    SmallCommittee,
    SmallCommitteeDepartment,
    SmallCommitteeMember,
)
from app.schemas.organization import (
    OrganizationPositionCreate,
    OrganizationPositionUpdate,
    SmallCommitteeCreate,
    SmallCommitteeUpdate,
)


def list_positions(db: Session):
    return (
        db.query(OrganizationPosition)
        .order_by(OrganizationPosition.level.asc(), OrganizationPosition.sort_order.asc().nullslast(), OrganizationPosition.id.asc())
        .all()
    )


def create_position(db: Session, payload: OrganizationPositionCreate):
    item = OrganizationPosition(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_position(db: Session, position_id: int, payload: OrganizationPositionUpdate):
    item = db.query(OrganizationPosition).filter(OrganizationPosition.id == position_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Organization position not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


def delete_position(db: Session, position_id: int) -> None:
    item = db.query(OrganizationPosition).filter(OrganizationPosition.id == position_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Organization position not found")
    db.delete(item)
    db.commit()


def list_small_committees(db: Session):
    return (
        db.query(SmallCommittee)
        .options(joinedload(SmallCommittee.departments).joinedload(SmallCommitteeDepartment.members))
        .order_by(SmallCommittee.id.desc())
        .all()
    )


def create_small_committee(db: Session, payload: SmallCommitteeCreate):
    committee = SmallCommittee(name=payload.name, description=payload.description)
    db.add(committee)
    db.commit()
    db.refresh(committee)

    for dept in payload.departments:
        db_dept = SmallCommitteeDepartment(committee_id=committee.id, name=dept.name)
        db.add(db_dept)
        db.commit()
        db.refresh(db_dept)

        for m in dept.members:
            db_member = SmallCommitteeMember(
                department_id=db_dept.id,
                family_member_id=m.family_member_id,
                member_name=m.member_name,
                role=m.role,
            )
            db.add(db_member)

        db.commit()

    return (
        db.query(SmallCommittee)
        .options(joinedload(SmallCommittee.departments).joinedload(SmallCommitteeDepartment.members))
        .filter(SmallCommittee.id == committee.id)
        .first()
    )


def update_small_committee(db: Session, committee_id: int, payload: SmallCommitteeUpdate):
    committee = db.query(SmallCommittee).filter(SmallCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=404, detail="Small committee not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(committee, key, value)

    db.commit()
    db.refresh(committee)
    return committee


def delete_small_committee(db: Session, committee_id: int) -> None:
    committee = db.query(SmallCommittee).filter(SmallCommittee.id == committee_id).first()
    if not committee:
        raise HTTPException(status_code=404, detail="Small committee not found")
    db.delete(committee)
    db.commit()
