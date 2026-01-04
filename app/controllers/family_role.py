from sqlalchemy.orm import Session

from app.models.family_role import FamilyRole
from app.schemas.family_role import FamilyRoleCreate, FamilyRoleUpdate


def get_all_family_roles(db: Session) -> list[FamilyRole]:
    return db.query(FamilyRole).order_by(FamilyRole.name.asc()).all()


def create_family_role(db: Session, role_in: FamilyRoleCreate) -> FamilyRole:
    existing = db.query(FamilyRole).filter(FamilyRole.name == role_in.name).first()
    if existing:
        raise ValueError("Role name already exists")

    role = FamilyRole(name=role_in.name, system_role=role_in.system_role)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_family_role(db: Session, role_id: int, role_in: FamilyRoleUpdate) -> FamilyRole:
    role = db.query(FamilyRole).filter(FamilyRole.id == role_id).first()
    if not role:
        raise ValueError("Role not found")

    if role_in.name is not None:
        name_conflict = (
            db.query(FamilyRole)
            .filter(FamilyRole.name == role_in.name, FamilyRole.id != role_id)
            .first()
        )
        if name_conflict:
            raise ValueError("Role name already exists")
        role.name = role_in.name

    if role_in.system_role is not None:
        role.system_role = role_in.system_role

    db.commit()
    db.refresh(role)
    return role


def delete_family_role(db: Session, role_id: int) -> None:
    role = db.query(FamilyRole).filter(FamilyRole.id == role_id).first()
    if not role:
        raise ValueError("Role not found")

    db.delete(role)
    db.commit()
