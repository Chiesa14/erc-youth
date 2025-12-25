from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import security
from app.core.security import get_current_user
from app.db.session import get_db
from app.controllers.user import get_user_by_email
from app.models.family_member import FamilyMember
from app.models.user import User
from app.schemas.user import RoleEnum
from app.schemas.token import Token

router = APIRouter()

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(db, form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = security.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

