import os
import uuid
import mimetypes
import logging
from typing import Optional, List
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from math import ceil

from app.models.shared_document import SharedDocument
from app.models.user import User
from app.schemas.shared_document import SharedDocumentOut, SharedDocumentList
from app.utils.logging_decorator import log_upload, log_view, log_update, log_delete

logger = logging.getLogger(__name__)

# Configuration
SHARED_DOCS_DIR = "uploads/shared_documents"
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.rtf',  # Documents
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',  # Images
    '.mp4', '.avi', '.mov', '.wmv', '.flv',  # Videos
    '.mp3', '.wav', '.aac', '.flac',  # Audio
    '.zip', '.rar', '.7z', '.tar', '.gz',  # Archives
    '.xls', '.xlsx', '.csv',  # Spreadsheets
    '.ppt', '.pptx'  # Presentations
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB for shared documents


def ensure_shared_docs_directory():
    """Ensure the shared documents directory exists"""
    os.makedirs(SHARED_DOCS_DIR, exist_ok=True)


def validate_shared_document_file(file: UploadFile) -> bool:
    """Validate uploaded shared document file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file extension
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    return True


@log_upload("shared_documents", "Uploaded shared document")
async def upload_shared_document(
        file: UploadFile,
        description: Optional[str],
        is_public: bool,
        db: Session,
        current_user: User
) -> SharedDocumentOut:
    """Upload a new shared document"""
    validate_shared_document_file(file)
    ensure_shared_docs_directory()

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(SHARED_DOCS_DIR, unique_filename)

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
    mime_type, _ = mimetypes.guess_type(file.filename)

    # Create SharedDocument record
    shared_doc = SharedDocument(
        name=file.filename,
        original_filename=file.filename,
        file_path=file_path,
        size=len(content),
        mime_type=mime_type,
        description=description,
        uploaded_by=current_user.id,
        is_public=is_public
    )

    db.add(shared_doc)
    db.commit()
    db.refresh(shared_doc)

    return convert_to_shared_document_out(shared_doc)


@log_view("shared_documents", "Viewed shared documents list")
async def get_shared_documents(
        db: Session,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        mime_type_filter: Optional[str] = None,
        include_flyers: bool = True,
        current_user: Optional[User] = None
) -> SharedDocumentList:
    """Get paginated list of shared documents"""

    # Base query - include all documents by default
    query = db.query(SharedDocument)

    # Optionally exclude announcement flyers
    if not include_flyers:
        query = query.filter(SharedDocument.announcement == None)

    # Filter by visibility (public or owned by current user)
    if current_user:
        query = query.filter(
            or_(
                SharedDocument.is_public == True,
                SharedDocument.uploaded_by == current_user.id
            )
        )
    else:
        query = query.filter(SharedDocument.is_public == True)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SharedDocument.name.ilike(search_term),
                SharedDocument.description.ilike(search_term)
            )
        )

    # Apply MIME type filter
    if mime_type_filter:
        query = query.filter(SharedDocument.mime_type.ilike(f"{mime_type_filter}%"))

    # Get total count
    total = query.count()

    # Apply pagination
    documents = query.offset((page - 1) * per_page).limit(per_page).all()

    # Convert to response models
    document_outs = [convert_to_shared_document_out(doc) for doc in documents]

    return SharedDocumentList(
        documents=document_outs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=ceil(total / per_page)
    )


@log_view("shared_documents", "Viewed shared document details")
async def get_shared_document(document_id: int, db: Session, current_user: Optional[User] = None) -> SharedDocumentOut:
    """Get a specific shared document"""
    document = db.query(SharedDocument).filter(SharedDocument.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access permissions
    if not document.is_public:
        if not current_user or document.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return convert_to_shared_document_out(document)


@log_update("shared_documents", "Updated shared document")
async def update_shared_document(
        document_id: int,
        name: Optional[str],
        description: Optional[str],
        is_public: Optional[bool],
        db: Session,
        current_user: User
) -> SharedDocumentOut:
    """Update shared document metadata"""
    document = db.query(SharedDocument).filter(SharedDocument.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check ownership
    if document.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this document")

    # Update fields
    if name is not None:
        document.name = name
    if description is not None:
        document.description = description
    if is_public is not None:
        document.is_public = is_public

    db.commit()
    db.refresh(document)

    return convert_to_shared_document_out(document)


@log_delete("shared_documents", "Deleted shared document")
async def delete_shared_document(document_id: int, db: Session, current_user: User):
    """Delete a shared document"""
    document = db.query(SharedDocument).filter(SharedDocument.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check ownership
    if document.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")

    # If this document is linked to an announcement, remove the link
    if document.announcement:
        document.announcement.flyer_id = None
        db.add(document.announcement)

    # Delete physical file
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        # Log the error but don't fail the deletion
        logger.warning(f"Could not delete file {document.file_path}: {str(e)}")

    db.delete(document)
    db.commit()

    return {"message": "Document deleted successfully"}


@log_view("shared_documents", "Downloaded shared document")
async def download_shared_document(document_id: int, db: Session, current_user: Optional[User] = None):
    """Download a shared document"""
    document = db.query(SharedDocument).filter(SharedDocument.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check access permissions
    if not document.is_public:
        if not current_user or document.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Check if file exists
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Increment download count
    document.downloads += 1
    db.commit()

    # Return file response
    from fastapi.responses import FileResponse
    return FileResponse(
        path=document.file_path,
        filename=document.original_filename,
        media_type=document.mime_type or 'application/octet-stream'
    )


@log_view("shared_documents", "Viewed document statistics")
async def get_document_stats(db: Session, include_flyers: bool = True) -> dict:
    """Get statistics about shared documents"""
    # Base query
    query = db.query(SharedDocument)
    if not include_flyers:
        query = query.filter(SharedDocument.announcement == None)

    # Total documents
    total_docs = query.count()

    # Total downloads
    total_downloads = query.with_entities(func.sum(SharedDocument.downloads)).scalar() or 0

    # Documents by type
    type_stats = query.with_entities(
        SharedDocument.mime_type,
        func.count(SharedDocument.id)
    ).group_by(SharedDocument.mime_type).all()

    # Recent uploads (last 7 days)
    from datetime import datetime, timedelta
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_uploads = query.filter(SharedDocument.uploaded_at >= seven_days_ago).count()

    # Flyer stats if including flyers
    flyer_stats = {}
    if include_flyers:
        flyer_count = db.query(SharedDocument).filter(SharedDocument.announcement != None).count()
        standalone_count = db.query(SharedDocument).filter(SharedDocument.announcement == None).count()
        flyer_stats = {
            "flyers": flyer_count,
            "standalone_documents": standalone_count
        }

    return {
        "total_documents": total_docs,
        "total_downloads": total_downloads,
        "recent_uploads": recent_uploads,
        "types": [{"mime_type": mime_type, "count": count} for mime_type, count in type_stats],
        **flyer_stats
    }


def convert_to_shared_document_out(document: SharedDocument) -> SharedDocumentOut:
    result = SharedDocumentOut.model_validate(document)
    # Set the computed flyer status
    result._is_flyer = document.is_flyer
    return result