from sqlalchemy.orm import joinedload

from app.controllers import bcc as bcc_controller
from app.db.session import SessionLocal
from app.models.family_member import FamilyMember


def main() -> None:
    db = SessionLocal()
    try:
        members = (
            db.query(FamilyMember)
            .options(joinedload(FamilyMember.bcc_class_completions))
            .order_by(FamilyMember.id.asc())
            .limit(25)
            .all()
        )

        for member in members:
            completed, missing, is_complete, percent = bcc_controller.compute_member_progress(member)
            print(
                f"member_id={member.id} name={member.name} is_complete={is_complete} percent={percent} completed={completed} missing={missing}"
            )

        incomplete = bcc_controller.list_incomplete_members(db)
        print(f"incomplete_total={len(incomplete)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
