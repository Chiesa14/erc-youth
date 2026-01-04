from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.bcc_class_completion import BccClassCompletion
from app.models.user import User


_BCC_CLASS_NUMBERS = list(range(1, 8))


def _validate_class_number(class_number: int) -> None:
    if class_number not in _BCC_CLASS_NUMBERS:
        raise HTTPException(status_code=400, detail="class_number must be between 1 and 7")


def get_member_with_bcc(db: Session, member_id: int) -> FamilyMember:
    member = (
        db.query(FamilyMember)
        .options(joinedload(FamilyMember.bcc_class_completions))
        .filter(FamilyMember.id == member_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found")
    return member


def compute_member_progress(member: FamilyMember) -> tuple[list[int], list[int], bool, float]:
    if member.bcc_class_participation:
        completed = _BCC_CLASS_NUMBERS.copy()
        missing: list[int] = []
        return completed, missing, True, 100.0

    completed_set = {c.class_number for c in (member.bcc_class_completions or [])}
    completed = sorted(completed_set)
    missing = [n for n in _BCC_CLASS_NUMBERS if n not in completed_set]
    is_complete = len(missing) == 0
    completion_percent = round((len(completed) / len(_BCC_CLASS_NUMBERS)) * 100, 1)
    return completed, missing, is_complete, completion_percent


def record_class_completion(
    db: Session,
    *,
    member_id: int,
    class_number: int,
    recorded_by: Optional[User],
) -> BccClassCompletion:
    _validate_class_number(class_number)

    member = get_member_with_bcc(db, member_id)

    existing = (
        db.query(BccClassCompletion)
        .filter(
            BccClassCompletion.member_id == member_id,
            BccClassCompletion.class_number == class_number,
        )
        .first()
    )
    if existing:
        return existing

    completion = BccClassCompletion(
        member_id=member_id,
        class_number=class_number,
        recorded_by_user_id=recorded_by.id if recorded_by else None,
    )
    db.add(completion)

    db.flush()
    if member.bcc_class_completions is not None:
        member.bcc_class_completions.append(completion)

    completed, missing, is_complete, _ = compute_member_progress(member)
    if is_complete and not member.bcc_class_participation:
        member.bcc_class_participation = True

    db.commit()
    db.refresh(completion)
    return completion


def list_incomplete_members(
    db: Session,
    *,
    family_id: Optional[int] = None,
) -> list[dict]:
    query = (
        db.query(FamilyMember)
        .options(
            joinedload(FamilyMember.bcc_class_completions),
            joinedload(FamilyMember.family),
        )
    )
    if family_id is not None:
        query = query.filter(FamilyMember.family_id == family_id)

    members = query.all()

    results: list[dict] = []
    for member in members:
        completed, missing, is_complete, completion_percent = compute_member_progress(member)
        if is_complete:
            continue

        family: Family | None = member.family
        results.append(
            {
                "member_id": member.id,
                "member_name": member.name,
                "phone": member.phone,
                "email": member.email,
                "family_id": member.family_id,
                "family_name": family.name if family else "Unknown",
                "family_category": family.category if family else "Unknown",
                "completed_classes": completed,
                "missing_classes": missing,
                "completion_percent": completion_percent,
            }
        )

    results.sort(key=lambda r: (r["family_category"], r["family_name"], r["member_name"]))
    return results


def get_family_completion_status(
    db: Session,
    *,
    family_id: int,
) -> tuple[bool, list[dict]]:
    members = (
        db.query(FamilyMember)
        .options(
            joinedload(FamilyMember.bcc_class_completions),
        )
        .filter(FamilyMember.family_id == family_id)
        .all()
    )

    incomplete: list[dict] = []
    for member in members:
        completed, missing, is_complete, completion_percent = compute_member_progress(member)
        if is_complete:
            continue
        incomplete.append(
            {
                "member_id": member.id,
                "member_name": member.name,
                "family_id": member.family_id,
                "completed_classes": completed,
                "missing_classes": missing,
                "is_complete": is_complete,
                "completion_percent": completion_percent,
            }
        )

    is_family_complete = len(incomplete) == 0
    incomplete.sort(key=lambda r: r["member_name"])
    return is_family_complete, incomplete
