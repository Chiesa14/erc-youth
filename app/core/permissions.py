from fastapi import HTTPException
from app.models.user import User
from app.schemas.user import RoleEnum

def require_parent(user: User) -> User:
    if user.role not in (RoleEnum.pere, RoleEnum.mere):
        raise HTTPException(status_code=403, detail="Only Père or Mère can perform this action.")
    return user
