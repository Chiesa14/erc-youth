from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import security
from app.core.security import get_current_user
from app.db.session import get_db
from app.controllers.user import get_user_by_email
from app.models.family_member import FamilyMember
from app.models.user import User
from app.models.chat import UserPresence
from app.schemas.user import RoleEnum
from app.schemas.token import Token

router = APIRouter()


def _upsert_user_presence(db: Session, user_id: int, *, is_online: bool) -> None:
    presence = db.query(UserPresence).filter(UserPresence.user_id == user_id).first()
    now = datetime.utcnow()

    if presence:
        presence.is_online = is_online
        presence.last_seen = now
    else:
        db.add(UserPresence(user_id=user_id, is_online=is_online, last_seen=now))

    db.commit()

@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user_by_email(db, form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Mark the user as online for presence tracking
    _upsert_user_presence(db, user.id, is_online=True)

    token = security.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Mark the user offline. (JWTs are stateless; this is presence only.)
    _upsert_user_presence(db, current_user.id, is_online=False)
    return None


@router.post("/heartbeat")
def heartbeat(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Keep last_seen fresh while the user is active.
    _upsert_user_presence(db, current_user.id, is_online=True)
    return {"ok": True, "user_id": current_user.id, "last_seen": datetime.utcnow().isoformat()}

