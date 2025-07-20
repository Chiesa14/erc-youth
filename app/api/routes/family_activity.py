from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.family_member import require_parent
from app.db.session import get_db
from app.models.user import User
from app.core.security import get_current_active_user
import app.controllers.family_activity as crud_activity
import app.schemas.family_activity as activity_schema
from app.schemas.family_activity import ActivityCategoryEnum

router = APIRouter(tags=["Activities"])

@router.post("/", response_model=activity_schema.ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    activity: activity_schema.ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Check if the user is a parent
    require_parent(current_user)

    # If family_id is not provided, assign it from the current user
    if not activity.family_id:
        if not current_user.family_id:
            raise HTTPException(status_code=400, detail="User is not assigned to a family.")
        activity_data = activity.model_copy(update={"family_id": current_user.family_id})
    else:
        activity_data = activity

    return crud_activity.create_activity(db, activity_data)


@router.get("/family/{family_id}", response_model=list[activity_schema.ActivityOut])
def read_activities_for_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Authorization check here as needed
    if current_user.family_id != family_id:
        raise HTTPException(status_code=403, detail="Not authorized to view activities for this family.")

    return crud_activity.get_activities_by_family(db, family_id)
