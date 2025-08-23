from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.permissions import get_admin_user, get_pastor_user
from app.core.security import get_current_user
from app.db.session import get_db
from app.controllers.feedback import (
    get_feedback_list,
    get_feedback_by_id,
    create_feedback,
    update_feedback,
    create_reply,
    get_new_feedback_count
)
from app.models.user import User
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackUpdate,
    FeedbackResponse,
    ReplyCreate,
    ReplyResponse
)
from app.schemas.user import RoleEnum

router = APIRouter()

@router.get("/", response_model=List[FeedbackResponse])
def read_feedback_list(
    status: str = Query("all", description="Filter by status: all, new, pending, resolved"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all feedback, optionally filtered by status
    """
    try:
        return get_feedback_list(db, status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feedback: {str(e)}")

@router.get("/new-count", response_model=int)
def read_new_feedback_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get count of new feedback items
    """
    try:
        return get_new_feedback_count(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching new feedback count: {str(e)}")

@router.get("/{feedback_id}", response_model=FeedbackResponse)
def read_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific feedback item by ID
    """
    try:
        return get_feedback_by_id(db, feedback_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feedback: {str(e)}")

@router.post("/", response_model=FeedbackResponse)
def create_new_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new feedback item
    """
    try:
        # Set the author based on current user
        feedback.author = current_user.full_name
        return create_feedback(db, feedback)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating feedback: {str(e)}")

@router.put("/{feedback_id}", response_model=FeedbackResponse)
def update_existing_feedback(
    feedback_id: int,
    feedback_update: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_pastor_user)
):
    """
    Update a feedback item - church pastor only
    """
    try:
        return update_feedback(db, feedback_id, feedback_update)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating feedback: {str(e)}")


@router.post("/{feedback_id}/reply", response_model=ReplyResponse)
def create_feedback_reply(
        feedback_id: int,
        reply: ReplyCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Determine author display based on role
        if current_user.role.value == RoleEnum.other:
            author = f"Youth Member {current_user.full_name}"
        else:
            author = f"{current_user.role.value} {current_user.full_name}"

        return create_reply(db, feedback_id, reply, author)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating reply: {str(e)}")