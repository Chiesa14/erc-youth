from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.core.permissions import get_admin_user, get_pastor_user
from app.core.security import get_current_user
from app.db.session import get_db
from app.controllers.recommendation import (
    get_pending_programs,
    get_family_comments,
    create_program,
    update_program_status,
    create_comment,
    get_all_recommendations,
    get_recommendations_summary
)
from app.models.user import User
from app.schemas.recommendation import (
    ProgramCreate,
    ProgramUpdate,
    ProgramResponse,
    CommentCreate,
    CommentResponse,
    RecommendationResponse,
    RecommendationSummaryResponse,
    PriorityEnum,
    CommentTypeEnum,
    ProgramStatusEnum
)

router = APIRouter()


@router.get("/programs/pending", response_model=List[ProgramResponse])
def read_pending_programs(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_pastor_user)
):
    """
    Get all pending programs for approval (church pastor only)
    """
    try:
        return get_pending_programs(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pending programs: {str(e)}")


@router.get("/all", response_model=List[RecommendationResponse])
def read_all_recommendations(
        family_ids: Optional[List[int]] = Query(None, description="Filter by family IDs"),
        start_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(None, description="Filter until this date (YYYY-MM-DD)"),
        program_status: Optional[List[ProgramStatusEnum]] = Query(None, description="Filter by program status"),
        comment_types: Optional[List[CommentTypeEnum]] = Query(None, description="Filter by comment types"),
        priority: Optional[List[PriorityEnum]] = Query(None, description="Filter by priority levels"),
        limit: Optional[int] = Query(None, description="Limit number of results", ge=1, le=1000),
        offset: Optional[int] = Query(None, description="Skip number of results", ge=0),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        return get_all_recommendations(
            db=db,
            family_ids=family_ids,
            start_date=start_date,
            end_date=end_date,
            program_status=program_status,
            priority=priority,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recommendations: {str(e)}")


@router.get("/summary", response_model=RecommendationSummaryResponse)
def read_recommendations_summary(
        family_ids: Optional[List[int]] = Query(None, description="Filter by family IDs"),
        start_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(None, description="Filter until this date (YYYY-MM-DD)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics for recommendations with optional filters.

    Returns counts and breakdowns of programs and comments by various categories.
    """
    try:
        return get_recommendations_summary(
            db=db,
            family_ids=family_ids,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recommendations summary: {str(e)}")


@router.get("/comments/family/{family_id}", response_model=List[CommentResponse])
def read_family_comments(
        family_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Get all comments for a specific family
    """
    try:
        return get_family_comments(db, family_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching family comments: {str(e)}")


@router.post("/programs", response_model=ProgramResponse)
def create_new_program(
        program: ProgramCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new program proposal
    """
    try:
        return create_program(db, program)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating program: {str(e)}")


@router.put("/programs/{program_id}/status", response_model=ProgramResponse)
def update_program_status_endpoint(
        program_id: int,
        program_update: ProgramUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_pastor_user)
):
    """
    Update the status of a program (approve/reject) - church pastor only
    """
    try:
        return update_program_status(db, program_id, program_update)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating program status: {str(e)}")


@router.post("/comments", response_model=CommentResponse)
def create_new_comment(
        comment: CommentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Create a new comment/recommendation
    """
    try:
        return create_comment(db, comment)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating comment: {str(e)}")