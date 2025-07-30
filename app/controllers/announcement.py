import os
import uuid
from typing import Optional
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.announcement import Announcement, AnnouncementView
from app.models.shared_document import SharedDocument
from app.models.user import User
from app.schemas.announcement import AnnouncementCreate, AnnouncementUpdate, AnnouncementOut

# Configuration
UPLOAD_DIR = "uploads/shared_documents"
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def ensure_upload_directory():
    """Ensure the upload directory exists"""
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def validate_file(file: UploadFile) -> bool:
    """Validate uploaded file"""
    if not file.filename:
        return False

    # Check file extension
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    return True


async def save_uploaded_file(file: UploadFile, db: Session, current_user: User) -> SharedDocument:
    """Save uploaded file and create SharedDocument record"""
    validate_file(file)
    ensure_upload_directory()

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file to disk
    try:
        content = await file.read()

        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )

        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # Get MIME type
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file.filename)

    # Create SharedDocument record
    shared_doc = SharedDocument(
        name=file.filename,
        original_filename=file.filename,
        file_path=file_path,
        size=len(content),
        mime_type=mime_type,
        uploaded_by=current_user.id,
        is_public=True  # Flyers are typically public
    )

    db.add(shared_doc)
    db.commit()
    db.refresh(shared_doc)

    return shared_doc


async def create_announcement(
        announcement: AnnouncementCreate,
        flyer: Optional[UploadFile],
        db: Session,
        current_user: User
) -> AnnouncementOut:
    """Create a new announcement"""
    flyer_id = None

    # Handle flyer upload if provided
    if flyer and flyer.filename:
        shared_doc = await save_uploaded_file(flyer, db, current_user)
        flyer_id = shared_doc.id

    # Create announcement
    db_announcement = Announcement(
        title=announcement.title,
        content=announcement.content,
        type=announcement.type,
        user_id=current_user.id,
        flyer_id=flyer_id
    )

    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)

    # Convert to response model
    return convert_to_announcement_out(db_announcement, db)


async def get_all_announcements(db: Session) -> list[AnnouncementOut]:
    """Get all announcements"""
    announcements = db.query(Announcement).all()
    return [convert_to_announcement_out(ann, db) for ann in announcements]


async def get_announcement(announcement_id: int, db: Session) -> AnnouncementOut:
    """Get a specific announcement"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return convert_to_announcement_out(announcement, db)


async def update_announcement(
        announcement_id: int,
        announcement: AnnouncementUpdate,
        flyer: Optional[UploadFile],
        db: Session,
        current_user: User
) -> AnnouncementOut:
    """Update an announcement"""
    db_announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not db_announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Check if user owns the announcement or is admin (you may need to adjust this logic)
    if db_announcement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this announcement")

    # Update fields if provided
    if announcement.title is not None:
        db_announcement.title = announcement.title
    if announcement.content is not None:
        db_announcement.content = announcement.content
    if announcement.type is not None:
        db_announcement.type = announcement.type

    # Handle flyer update if provided
    if flyer and flyer.filename:
        # Delete old flyer if exists
        if db_announcement.flyer_id:
            old_flyer = db.query(SharedDocument).filter(SharedDocument.id == db_announcement.flyer_id).first()
            if old_flyer:
                # Delete the physical file
                if os.path.exists(old_flyer.file_path):
                    os.remove(old_flyer.file_path)
                db.delete(old_flyer)

        # Save new flyer
        shared_doc = await save_uploaded_file(flyer, db, current_user)
        db_announcement.flyer_id = shared_doc.id

    db_announcement.updated_at = func.now()
    db.commit()
    db.refresh(db_announcement)

    return convert_to_announcement_out(db_announcement, db)


async def delete_announcement(announcement_id: int, db: Session, current_user: User):
    """Delete an announcement"""
    db_announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not db_announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Check if user owns the announcement or is admin
    if db_announcement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this announcement")

    # Delete associated flyer if exists
    if db_announcement.flyer_id:
        flyer = db.query(SharedDocument).filter(SharedDocument.id == db_announcement.flyer_id).first()
        if flyer:
            # Delete the physical file
            if os.path.exists(flyer.file_path):
                os.remove(flyer.file_path)
            db.delete(flyer)

    db.delete(db_announcement)
    db.commit()

    return {"message": "Announcement deleted successfully"}


async def download_flyer(announcement_id: int, db: Session):
    """Download announcement flyer"""
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if not announcement.flyer_id:
        raise HTTPException(status_code=404, detail="No flyer attached to this announcement")

    flyer = db.query(SharedDocument).filter(SharedDocument.id == announcement.flyer_id).first()
    if not flyer:
        raise HTTPException(status_code=404, detail="Flyer not found")

    # Increment download count
    flyer.downloads += 1
    db.commit()

    # Return file response (you'll need to implement this based on your file serving strategy)
    from fastapi.responses import FileResponse

    if not os.path.exists(flyer.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=flyer.file_path,
        filename=flyer.original_filename,
        media_type=flyer.mime_type or 'application/octet-stream'
    )


def convert_to_announcement_out(announcement: Announcement, db: Session) -> AnnouncementOut:
    # Get view count
    view_count = db.query(func.count(AnnouncementView.id)).filter(
        AnnouncementView.announcement_id == announcement.id
    ).scalar() or 0

    # Create the response object
    result = AnnouncementOut.model_validate(announcement)
    result._view_count = view_count

    return result