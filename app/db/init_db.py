from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import RoleEnum, GenderEnum, FamilyCategoryEnum
from app.core.security import get_password_hash
from app.db.session import SessionLocal, Base, engine
from app.core.timestamp_middleware import init_timestamp_middleware


def init_db():
    # Initialize timestamp middleware
    init_timestamp_middleware()
    
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
            gender=GenderEnum.male,
            phone="+250796198140",
            role=RoleEnum.admin,
        )
        db.add(admin_user)
        print("Default admin user created.")
    else:
        print("Admin user already exists.")

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
        print("Default church pastor user created.")
    else:
        print("Church pastor user already exists.")

    db.commit()
    db.close()