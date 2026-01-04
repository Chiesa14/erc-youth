from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.user import User
from app.models.family_role import FamilyRole
from app.schemas.user import RoleEnum, GenderEnum, FamilyCategoryEnum
from app.core.security import get_password_hash
from app.db.session import SessionLocal, Base, engine
from app.core.timestamp_middleware import init_timestamp_middleware
import logging

logger = logging.getLogger(__name__)


def _get_table_columns(conn, table_name: str) -> set[str]:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
        return {r.get("name") for r in rows if r.get("name")}

    if dialect in {"postgresql", "postgres"}:
        rows = conn.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :table_name
                """
            ),
            {"table_name": table_name},
        ).all()
        return {r[0] for r in rows if r and r[0]}

    return set()


def _ensure_family_activities_date_range_columns() -> None:
    table = "family_activities"
    with engine.begin() as conn:
        existing = _get_table_columns(conn, table)

        dialect = conn.dialect.name
        if "start_date" not in existing:
            if dialect in {"postgresql", "postgres"}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS start_date DATE"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN start_date DATE"))

        if "end_date" not in existing:
            if dialect in {"postgresql", "postgres"}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS end_date DATE"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN end_date DATE"))

        conn.execute(text(f"UPDATE {table} SET start_date = \"date\" WHERE start_date IS NULL"))
        conn.execute(text(f"UPDATE {table} SET end_date = \"date\" WHERE end_date IS NULL"))


def _ensure_users_name_and_role_columns() -> None:
    table = "users"
    with engine.begin() as conn:
        existing = _get_table_columns(conn, table)

        dialect = conn.dialect.name
        columns_to_add: list[tuple[str, str]] = [
            ("first_name", "VARCHAR"),
            ("last_name", "VARCHAR"),
            ("deliverance_name", "VARCHAR"),
            ("family_role_id", "INTEGER"),
        ]

        for col_name, col_type in columns_to_add:
            if col_name in existing:
                continue

            if dialect in {"postgresql", "postgres"}:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))

def init_db():
    # Initialize timestamp middleware
    init_timestamp_middleware()
    
    # Create tables
    Base.metadata.create_all(bind=engine)

    _ensure_family_activities_date_range_columns()
    _ensure_users_name_and_role_columns()

    db: Session = SessionLocal()

    # Check if admin user already exists
    admin_email = "admin@gmail.com"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        admin_user = User(
            full_name="Admin User",
            email=admin_email,
            hashed_password=get_password_hash("admin!123"),
            gender=GenderEnum.male,
            phone="+250796198140",
            role=RoleEnum.admin,
        )
        db.add(admin_user)
        logger.info("Default admin user created.")
    else:
        logger.info("Admin user already exists.")

    # Check if church pastor user already exists
    pastor_email = "pastor@church.com"
    pastor = db.query(User).filter(User.email == pastor_email).first()
    if not pastor:
        pastor_user = User(
            full_name="Church Pastor",
            email=pastor_email,
            hashed_password=get_password_hash("pastor!123"),
            gender=GenderEnum.male,  # You can change this as needed
            phone="+250796198141",
            role=RoleEnum.church_pastor,
            biography="Church pastor responsible for spiritual guidance and church activities."
        )
        db.add(pastor_user)
        logger.info("Default church pastor user created.")
    else:
        logger.info("Church pastor user already exists.")

    db.commit()

    default_family_roles: list[tuple[str, RoleEnum]] = [
        ("Pere", RoleEnum.pere),
        ("Mere", RoleEnum.mere),
        ("Youth Leader", RoleEnum.other),
        ("Pastor", RoleEnum.church_pastor),
        ("Admin", RoleEnum.admin),
    ]

    for name, system_role in default_family_roles:
        existing_role = db.query(FamilyRole).filter(FamilyRole.name == name).first()
        if not existing_role:
            db.add(FamilyRole(name=name, system_role=system_role))

    db.commit()
    db.close()