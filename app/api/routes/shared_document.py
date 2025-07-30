from operator import or_

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.controllers import shared_document
from app.db.session import get_db
from app.models.shared_document import SharedDocument
from app.schemas.shared_document import SharedDocumentOut, SharedDocumentList
from app.models.user import User
from app.core.security import get_current_user,get_current_active_user

router = APIRouter()


@router.post("/upload", response_model=SharedDocumentOut)
async def upload_shared_document_route(
        file: UploadFile = File(...),
        description: Optional[str] = Form(None),
        is_public: bool = Form(True),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Upload a new shared document"""
    return await shared_document.upload_shared_document(file, description, is_public, db, current_user)


@router.get("/", response_model=SharedDocumentList)
async def get_shared_documents_route(
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        search: Optional[str] = Query(None, description="Search in name and description"),
        mime_type: Optional[str] = Query(None, description="Filter by MIME type (e.g., 'image', 'application/pdf')"),
        include_flyers: bool = Query(True, description="Include announcement flyers in results"),
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """Get paginated list of shared documents"""
    return await shared_document.get_shared_documents(
        db, page, per_page, search, mime_type, include_flyers, current_user
    )


@router.get("/stats")
async def get_document_stats_route(
        include_flyers: bool = Query(True, description="Include flyers in statistics"),
        db: Session = Depends(get_db)
):
    """Get statistics about shared documents"""
    return await shared_document.get_document_stats(db, include_flyers)


@router.get("/{document_id}", response_model=SharedDocumentOut)
async def get_shared_document_route(
        document_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """Get details of a specific shared document"""
    return await shared_document.get_shared_document(document_id, db, current_user)


@router.put("/{document_id}", response_model=SharedDocumentOut)
async def update_shared_document_route(
        document_id: int,
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        is_public: Optional[bool] = Form(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Update shared document metadata"""
    return await shared_document.update_shared_document(
        document_id, name, description, is_public, db, current_user
    )


@router.delete("/{document_id}")
async def delete_shared_document_route(
        document_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Delete a shared document"""
    return await shared_document.delete_shared_document(document_id, db, current_user)


@router.get("/{document_id}/download")
async def download_shared_document_route(
        document_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """Download a shared document"""
    return await shared_document.download_shared_document(document_id, db, current_user)


@router.get("/user/{user_id}", response_model=SharedDocumentList)
async def get_user_documents_route(
        user_id: int,
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        include_flyers: bool = Query(True, description="Include announcement flyers"),
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """Get documents uploaded by a specific user"""
    from app.controllers.shared_document import get_shared_documents
    from sqlalchemy import and_

    # Base query for user's documents
    query = db.query(SharedDocument).filter(SharedDocument.uploaded_by == user_id)

    # Optionally exclude flyers
    if not include_flyers:
        query = query.filter(SharedDocument.announcement == None)

    # Filter by visibility if not the owner
    if not current_user or current_user.id != user_id:
        query = query.filter(SharedDocument.is_public == True)

    total = query.count()
    documents = query.offset((page - 1) * per_page).limit(per_page).all()

    from math import ceil
    from app.controllers.shared_document import convert_to_shared_document_out

    document_outs = [convert_to_shared_document_out(doc) for doc in documents]

    return SharedDocumentList(
        documents=document_outs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=ceil(total / per_page) if total > 0 else 0
    )


@router.get("/types/list")
async def get_document_types_route(
        include_flyers: bool = Query(True, description="Include flyers in type listing"),
        db: Session = Depends(get_db)
):
    """Get list of available document types/MIME types"""
    from sqlalchemy import func, distinct

    query = db.query(distinct(SharedDocument.mime_type)).filter(
        SharedDocument.mime_type.isnot(None)
    )

    # Optionally exclude flyers
    if not include_flyers:
        query = query.filter(SharedDocument.announcement == None)

    mime_types = query.all()

    # Group by category
    categories = {
        'documents': [],
        'images': [],
        'videos': [],
        'audio': [],
        'archives': [],
        'other': []
    }

    for (mime_type,) in mime_types:
        if mime_type.startswith('application/'):
            if 'pdf' in mime_type or 'document' in mime_type or 'text' in mime_type:
                categories['documents'].append(mime_type)
            elif 'zip' in mime_type or 'rar' in mime_type or 'archive' in mime_type:
                categories['archives'].append(mime_type)
            else:
                categories['other'].append(mime_type)
        elif mime_type.startswith('image/'):
            categories['images'].append(mime_type)
        elif mime_type.startswith('video/'):
            categories['videos'].append(mime_type)
        elif mime_type.startswith('audio/'):
            categories['audio'].append(mime_type)
        else:
            categories['other'].append(mime_type)


# Add these new endpoints at the end of the router

@router.get("/flyers", response_model=SharedDocumentList)
async def get_flyers_only_route(
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        search: Optional[str] = Query(None, description="Search in name and description"),
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """Get only announcement flyers"""
    from sqlalchemy import and_
    from app.controllers.shared_document import convert_to_shared_document_out
    from math import ceil

    # Query only documents that are linked to announcements
    query = db.query(SharedDocument).filter(SharedDocument.announcement != None)

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                SharedDocument.name.ilike(search_term),
                SharedDocument.description.ilike(search_term)
            )
        )

    # Filter by visibility
    if current_user:
        query = query.filter(
            or_(
                SharedDocument.is_public == True,
                SharedDocument.uploaded_by == current_user.id
            )
        )
    else:
        query = query.filter(SharedDocument.is_public == True)

    total = query.count()
    documents = query.offset((page - 1) * per_page).limit(per_page).all()

    document_outs = [convert_to_shared_document_out(doc) for doc in documents]

    return SharedDocumentList(
        documents=document_outs,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=ceil(total / per_page) if total > 0 else 0
    )


@router.get("/standalone", response_model=SharedDocumentList)
async def get_standalone_documents_route(
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        search: Optional[str] = Query(None, description="Search in name and description"),
        mime_type: Optional[str] = Query(None, description="Filter by MIME type"),
        db: Session = Depends(get_db),
        current_user: Optional[User] = Depends(get_current_user)
):
    """Get only standalone documents (not flyers)"""
    return await shared_document.get_shared_documents(
        db, page, per_page, search, mime_type, include_flyers=False, current_user=current_user
    )


@router.post("/{document_id}/link-to-announcement")
async def link_document_to_announcement_route(
        document_id: int,
        announcement_id: int = Form(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Link an existing document to an announcement as a flyer"""
    from app.models.announcement import Announcement

    # Get the document
    document = db.query(SharedDocument).filter(SharedDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check ownership of document
    if document.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this document")

    # Get the announcement
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Check ownership of announcement
    if announcement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this announcement")

    # Check if announcement already has a flyer
    if announcement.flyer_id:
        raise HTTPException(status_code=400, detail="Announcement already has a flyer")

    # Link the document to the announcement
    announcement.flyer_id = document_id
    db.commit()

    return {"message": "Document successfully linked to announcement as flyer"}


@router.delete("/{document_id}/unlink-from-announcement")
async def unlink_document_from_announcement_route(
        document_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Unlink a document from its announcement (remove flyer status)"""
    from app.models.announcement import Announcement

    # Get the document
    document = db.query(SharedDocument).filter(SharedDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if document is linked to an announcement
    if not document.announcement:
        raise HTTPException(status_code=400, detail="Document is not linked to any announcement")

    # Check ownership
    if document.uploaded_by != current_user.id and document.announcement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this link")

    # Remove the link
    document.announcement.flyer_id = None
    db.commit()

    return {"message": "Document successfully unlinked from announcement"}