from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import RoleEnum, GenderEnum, FamilyCategoryEnum
from app.core.security import get_password_hash
from app.db.session import SessionLocal, Base, engine


def init_db():
    # Create tables
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    # Check if admin user already exists
    admin_email = "admin@gmail.com"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        admin_user = User(
            full_name="Admin User",
            email=admin_email,
            hashed_password=get_password_hash("admin!123"),
            gender=GenderEnum.male,            # required enum
            phone="+250796198140",                # fill with fake or valid phone
            role=RoleEnum.admin,
        )
        db.add(admin_user)

        db.commit()
        print("Default admin user created.")
    else:
        print("Admin user already exists.")

    db.close()
