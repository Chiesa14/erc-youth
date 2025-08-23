from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException
from datetime import date, datetime
from app.db.session import SessionLocal
from app.models.recommendation import Program, Comment
from app.models.family import Family
from app.schemas.recommendation import (
    ProgramCreate, ProgramUpdate, ProgramResponse,
    CommentCreate, CommentResponse, RecommendationResponse,
    PriorityEnum, CommentTypeEnum, ProgramStatusEnum
)
from app.utils.timestamps import to_iso_format, add_timestamps_to_dict


def get_pending_programs(db: Session) -> List[ProgramResponse]:
    """
    Get all pending programs for approval
    """
    programs = db.query(Program).filter(Program.status == "pending").all()

    result = []
    for program in programs:
        family = db.query(Family).filter(Family.id == program.family_id).first()
        program_data = ProgramResponse(
            id=program.id,
            family_id=program.family_id,
            family_name=family.name if family else "Unknown",
            program_name=program.program_name,
            description=program.description,
            submitted_date=program.submitted_date,
            requested_budget=program.requested_budget,
            participants=program.participants,
            priority=program.priority,
            status=program.status
        )
        result.append(program_data)

    return result


def get_all_recommendations(
        db: Session,
        family_ids: Optional[List[int]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        program_status: Optional[List[ProgramStatusEnum]] = None,
        priority: Optional[List[PriorityEnum]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
) -> List[RecommendationResponse]:
    """
    Get all recommendations (only programs) with optional filters
    """
    recommendations = []

    # Build program query with filters
    program_query = db.query(Program).join(Family)

    # Apply family filter
    if family_ids:
        program_query = program_query.filter(Program.family_id.in_(family_ids))

    # Apply date filters
    if start_date:
        program_query = program_query.filter(Program.submitted_date >= start_date)
    if end_date:
        program_query = program_query.filter(Program.submitted_date <= end_date)

    # Apply status filter
    if program_status:
        program_query = program_query.filter(Program.status.in_(program_status))

    # Apply priority filter
    if priority:
        program_query = program_query.filter(Program.priority.in_(priority))

    programs = program_query.all()

    # Convert programs to recommendations
    for program in programs:
        family = db.query(Family).filter(Family.id == program.family_id).first()
        recommendation = RecommendationResponse(
            id=program.id,
            type="program",
            family_id=program.family_id,
            family_name=family.name if family else "Unknown",
            family_category=family.category if family and hasattr(family, 'category') else "Unknown",
            title=program.program_name,
            description=program.description,
            date=program.submitted_date,
            status=program.status.value,
            priority=program.priority.value if program.priority else None,
            requested_budget=program.requested_budget,
            participants=program.participants,
            comment_type=None
        )
        recommendations.append(recommendation)

    # Sort by date (newest first)
    recommendations.sort(key=lambda x: x.date, reverse=True)

    # Apply pagination
    if offset:
        recommendations = recommendations[offset:]
    if limit:
        recommendations = recommendations[:limit]

    return recommendations


def get_recommendations_summary(
        db: Session,
        family_ids: Optional[List[int]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
) -> dict:
    """
    Get summary statistics for recommendations
    """
    # Build base queries
    program_query = db.query(Program)
    comment_query = db.query(Comment)

    # Apply filters
    if family_ids:
        program_query = program_query.filter(Program.family_id.in_(family_ids))
        comment_query = comment_query.filter(Comment.family_id.in_(family_ids))

    if start_date:
        program_query = program_query.filter(Program.submitted_date >= start_date)
        comment_query = comment_query.filter(Comment.date >= start_date)

    if end_date:
        program_query = program_query.filter(Program.submitted_date <= end_date)
        comment_query = comment_query.filter(Comment.date <= end_date)

    # Get counts
    total_programs = program_query.count()
    pending_programs = program_query.filter(Program.status == ProgramStatusEnum.pending).count()
    approved_programs = program_query.filter(Program.status == ProgramStatusEnum.approved).count()
    rejected_programs = program_query.filter(Program.status == ProgramStatusEnum.rejected).count()

    total_comments = comment_query.count()

    # Get program counts by priority
    high_priority = program_query.filter(Program.priority == PriorityEnum.high).count()
    medium_priority = program_query.filter(Program.priority == PriorityEnum.medium).count()
    low_priority = program_query.filter(Program.priority == PriorityEnum.low).count()

    # Get comment counts by type
    comment_type_counts = {}
    for comment_type in CommentTypeEnum:
        count = comment_query.filter(Comment.comment_type == comment_type).count()
        comment_type_counts[comment_type.value] = count

    return {
        "total_recommendations": total_programs + total_comments,
        "programs": {
            "total": total_programs,
            "pending": pending_programs,
            "approved": approved_programs,
            "rejected": rejected_programs,
            "by_priority": {
                "high": high_priority,
                "medium": medium_priority,
                "low": low_priority
            }
        },
        "comments": {
            "total": total_comments,
            "by_type": comment_type_counts
        }
    }


def get_family_comments(db: Session, family_id: int) -> List[CommentResponse]:
    """
    Get all comments for a specific family
    """
    comments = db.query(Comment).filter(Comment.family_id == family_id).all()

    result = []
    for comment in comments:
        family = db.query(Family).filter(Family.id == comment.family_id).first()
        comment_data = CommentResponse(
            id=comment.id,
            family_id=comment.family_id,
            family_name=family.name if family else "Unknown",
            comment=comment.comment,
            date=comment.date,
            comment_type=comment.comment_type,
            status=comment.status
        )
        result.append(comment_data)

    return result


def create_program(db: Session, program: ProgramCreate) -> ProgramResponse:
    """
    Create a new program proposal
    """
    # Check if family exists
    family = db.query(Family).filter(Family.id == program.family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    # Create new program
    db_program = Program(
        family_id=program.family_id,
        program_name=program.program_name,
        description=program.description,
        requested_budget=program.requested_budget,
        participants=program.participants,
        priority=program.priority
    )

    db.add(db_program)
    db.commit()
    db.refresh(db_program)

    return ProgramResponse(
        id=db_program.id,
        family_id=db_program.family_id,
        family_name=family.name,
        program_name=db_program.program_name,
        description=db_program.description,
        submitted_date=db_program.submitted_date,
        requested_budget=db_program.requested_budget,
        participants=db_program.participants,
        priority=db_program.priority,
        status=db_program.status
    )


def update_program_status(db: Session, program_id: int, program_update: ProgramUpdate) -> ProgramResponse:
    """
    Update the status of a program (approve/reject)
    """
    db_program = db.query(Program).filter(Program.id == program_id).first()
    if not db_program:
        raise HTTPException(status_code=404, detail="Program not found")

    # Update program status
    db_program.status = program_update.status
    db.commit()
    db.refresh(db_program)

    family = db.query(Family).filter(Family.id == db_program.family_id).first()

    return ProgramResponse(
        id=db_program.id,
        family_id=db_program.family_id,
        family_name=family.name if family else "Unknown",
        program_name=db_program.program_name,
        description=db_program.description,
        submitted_date=db_program.submitted_date,
        requested_budget=db_program.requested_budget,
        participants=db_program.participants,
        priority=db_program.priority,
        status=db_program.status
    )


def create_comment(db: Session, comment: CommentCreate) -> CommentResponse:
    """
    Create a new comment/recommendation
    """
    # Check if family exists
    family = db.query(Family).filter(Family.id == comment.family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")

    # Create new comment
    db_comment = Comment(
        family_id=comment.family_id,
        comment=comment.comment,
        comment_type=comment.comment_type
    )

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    return CommentResponse(
        id=db_comment.id,
        family_id=db_comment.family_id,
        family_name=family.name,
        comment=db_comment.comment,
        date=db_comment.date,
        comment_type=db_comment.comment_type,
        status=db_comment.status
    )