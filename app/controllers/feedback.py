from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from app.db.session import SessionLocal
from app.models.feedback import Feedback, Reply
from app.models.family import Family
from app.schemas.feedback import FeedbackCreate, FeedbackUpdate, FeedbackResponse, ReplyCreate, ReplyResponse
from app.utils.timestamps import to_iso_format, add_timestamps_to_dict
from app.utils.logging_decorator import log_create, log_update, log_view

@log_view("feedback", "Viewed feedback list")
def get_feedback_list(db: Session, status_filter: str = None) -> List[FeedbackResponse]:
    """
    Get all feedback, optionally filtered by status
    """
    query = db.query(Feedback)
    
    if status_filter and status_filter != "all":
        query = query.filter(Feedback.status == status_filter)
    
    feedback_items = query.all()
    
    result = []
    for feedback in feedback_items:
        family = db.query(Family).filter(Family.id == feedback.family_id).first()
        
        # Get replies for this feedback
        replies = []
        for reply in feedback.replies:
            reply_data = ReplyResponse(
                id=reply.id,
                author=reply.author,
                content=reply.content,
                date=reply.date
            )
            replies.append(reply_data)
        
        feedback_data = FeedbackResponse(
            id=feedback.id,
            family_id=feedback.family_id,
            family_name=family.name if family else "Unknown",
            author=feedback.author,
            subject=feedback.subject,
            content=feedback.content,
            rating=feedback.rating,
            date=feedback.date,
            status=feedback.status,
            category=feedback.category,
            parent_notified=feedback.parent_notified,
            replies=replies
        )
        result.append(feedback_data)
    
    return result

@log_view("feedback", "Viewed feedback details")
def get_feedback_by_id(db: Session, feedback_id: int) -> FeedbackResponse:
    """
    Get a specific feedback item by ID
    """
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    family = db.query(Family).filter(Family.id == feedback.family_id).first()
    
    # Get replies for this feedback
    replies = []
    for reply in feedback.replies:
        reply_data = ReplyResponse(
            id=reply.id,
            author=reply.author,
            content=reply.content,
            date=reply.date
        )
        replies.append(reply_data)
    
    return FeedbackResponse(
        id=feedback.id,
        family_id=feedback.family_id,
        family_name=family.name if family else "Unknown",
        author=feedback.author,
        subject=feedback.subject,
        content=feedback.content,
        rating=feedback.rating,
        date=feedback.date,
        status=feedback.status,
        category=feedback.category,
        parent_notified=feedback.parent_notified,
        replies=replies
    )

@log_create("feedback", "Created new feedback")
def create_feedback(db: Session, feedback: FeedbackCreate) -> FeedbackResponse:
    """
    Create a new feedback item
    """
    # Check if family exists
    family = db.query(Family).filter(Family.id == feedback.family_id).first()
    if not family:
        raise HTTPException(status_code=404, detail="Family not found")
    
    # Create new feedback
    db_feedback = Feedback(
        family_id=feedback.family_id,
        author=feedback.author,
        subject=feedback.subject,
        content=feedback.content,
        category=feedback.category,
        rating=feedback.rating
    )
    
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    
    return FeedbackResponse(
        id=db_feedback.id,
        family_id=db_feedback.family_id,
        family_name=family.name,
        author=db_feedback.author,
        subject=db_feedback.subject,
        content=db_feedback.content,
        rating=db_feedback.rating,
        date=db_feedback.date,
        status=db_feedback.status,
        category=db_feedback.category,
        parent_notified=db_feedback.parent_notified,
        replies=[]
    )

@log_update("feedback", "Updated feedback status")
def update_feedback(db: Session, feedback_id: int, feedback_update: FeedbackUpdate) -> FeedbackResponse:
    """
    Update a feedback item
    """
    db_feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not db_feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Update feedback fields
    if feedback_update.status is not None:
        db_feedback.status = feedback_update.status
    if feedback_update.parent_notified is not None:
        db_feedback.parent_notified = feedback_update.parent_notified
    
    db.commit()
    db.refresh(db_feedback)
    
    family = db.query(Family).filter(Family.id == db_feedback.family_id).first()
    
    # Get replies for this feedback
    replies = []
    for reply in db_feedback.replies:
        reply_data = ReplyResponse(
            id=reply.id,
            author=reply.author,
            content=reply.content,
            date=reply.date
        )
        replies.append(reply_data)
    
    return FeedbackResponse(
        id=db_feedback.id,
        family_id=db_feedback.family_id,
        family_name=family.name if family else "Unknown",
        author=db_feedback.author,
        subject=db_feedback.subject,
        content=db_feedback.content,
        rating=db_feedback.rating,
        date=db_feedback.date,
        status=db_feedback.status,
        category=db_feedback.category,
        parent_notified=db_feedback.parent_notified,
        replies=replies
    )


@log_create("feedback_replies", "Created feedback reply")
def create_reply(db: Session, feedback_id: int, reply: ReplyCreate, author: str = None) -> ReplyResponse:
    """
    Create a reply to a feedback item
    """
    # Check if feedback exists
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    # Create new reply with provided author or default
    db_reply = Reply(
        feedback_id=feedback_id,
        author=author or (reply.author if hasattr(reply, 'author') else "Staff"),
        content=reply.content
    )

    db.add(db_reply)
    db.commit()
    db.refresh(db_reply)

    return ReplyResponse(
        id=db_reply.id,
        author=db_reply.author,
        content=db_reply.content,
        date=db_reply.date
    )

@log_view("feedback", "Viewed new feedback count")
def get_new_feedback_count(db: Session) -> int:
    """
    Get count of new feedback items
    """
    return db.query(Feedback).filter(Feedback.status == "new").count()