from fastapi import HTTPException, Depends
from starlette import status

from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import RoleEnum

def require_parent(user: User) -> User:
    if user.role not in (RoleEnum.pere, RoleEnum.mere):
        raise HTTPException(status_code=403, detail="Only Père or Mère can perform this action.")
    return user


# Dependency to check if the user is an admin
def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized: Admin access required"
        )
    return current_user