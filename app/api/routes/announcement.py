import uuid

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.controllers import announcement
from app.controllers.announcement import create_announcement
from app.db.session import get_db
from app.schemas.announcement import AnnouncementOut, AnnouncementCreate, AnnouncementUpdate, AnnouncementType
from app.models.user import User
from app.core.security import get_current_user

router = APIRouter()


@router.post("/", response_model=AnnouncementOut)
async def create_announcement_route(
        title: str = Form(...),
        content: str = Form(...),
        type: AnnouncementType = Form(...),
        flyer: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Create the announcement object from form data
    announcement_data = AnnouncementCreate(
        title=title,
        content=content,
        type=type
    )
    return await create_announcement(announcement_data, flyer, db, current_user)



@router.get("/", response_model=list[AnnouncementOut])
async def get_all_announcements_route(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user, use_cache=False),
    request: Request = None
):
    session_id = request.cookies.get("session_id") if request else str(uuid.uuid4())
    return await announcement.get_all_announcements(db, current_user, session_id)


@router.get("/{announcement_id}", response_model=AnnouncementOut)
async def get_announcement_route(announcement_id: int, db: Session = Depends(get_db)):
    return await announcement.get_announcement(announcement_id, db)


@router.put("/{announcement_id}", response_model=AnnouncementOut)
async def update_announcement_route(
        announcement_id: int,
        title: Optional[str] = Form(None),
        content: Optional[str] = Form(None),
        type: Optional[AnnouncementType] = Form(None),
        flyer: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Create the update object from form data, only including non-None values
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if content is not None:
        update_data["content"] = content
    if type is not None:
        update_data["type"] = type

    announcement_update = AnnouncementUpdate(**update_data)
    return await announcement.update_announcement(announcement_id, announcement_update, flyer, db, current_user)


@router.delete("/{announcement_id}")
async def delete_announcement_route(
        announcement_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return await announcement.delete_announcement(announcement_id, db, current_user)


@router.get("/{announcement_id}/flyer")
async def download_flyer_route(
    announcement_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    return await announcement.download_flyer(announcement_id, db, request)
