from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.models import Family
from app.models.family_document import FamilyDocument
from app.schemas.family_document import DocumentType, DocumentOut, ReportStatus, LetterStatus
from app.controllers import family_document as doc_controller
from app.core.security import get_db, get_current_active_user, get_current_admin_user, get_current_admin_or_pastor_user
from app.models.user import User

router = APIRouter(tags=["Documents"])


@router.get("/", response_model=list[DocumentOut])
async def list_documents(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
        skip: int = 0,
        limit: Optional[int] = None,
        x_total_count: bool = Header(default=False)
):
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User has no assigned family")

    query = db.query(FamilyDocument).filter_by(family_id=current_user.family_id).order_by(
        FamilyDocument.uploaded_at.desc())

    # Get total count if requested
    total_count = query.count() if x_total_count else None

    # Apply pagination
    if limit is not None:
        documents = query.offset(skip).limit(limit).all()
    else:
        documents = query.all()

    # Include total count in response headers
    headers = {"X-Total-Count": str(total_count)} if total_count is not None else {}

    # Use model_dump to serialize the Pydantic models
    return JSONResponse(
        content=[DocumentOut.model_validate(doc).model_dump() for doc in documents],
        headers=headers
    )


@router.post("/upload", response_model=DocumentOut)
def upload_document(
        type: DocumentType,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User has no assigned family")

    return doc_controller.upload_family_document(db, current_user.family_id, type, file)


@router.get("/{doc_id}/download")
def download_document(
        doc_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    doc = doc_controller.get_document_by_id(db, doc_id, current_user.family_id)
    return FileResponse(doc.file_path, filename=doc.original_filename)


@router.delete("/{doc_id}")
def delete_document(
        doc_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    doc = doc_controller.get_document_by_id(db, doc_id, current_user.family_id)
    doc_controller.delete_document(db, doc)
    return {"detail": "Document deleted"}


@router.patch("/{doc_id}/status")
def update_document_status(
        doc_id: int,
        status: str = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    doc = doc_controller.get_document_by_id(db, doc_id, current_user.family_id)

    # Validate allowed statuses per type
    if doc.type == DocumentType.report and status not in [s.value for s in ReportStatus]:
        raise HTTPException(status_code=400, detail="Invalid status for report")
    if doc.type == DocumentType.letter and status not in [s.value for s in LetterStatus]:
        raise HTTPException(status_code=400, detail="Invalid status for letter")

    doc.status = status
    db.commit()
    db.refresh(doc)
    return {"detail": "Status updated", "status": doc.status}


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
        doc_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    return doc_controller.get_document_by_id(db, doc_id, current_user.family_id)


@router.get("/all-docs/stats")
def document_statistics(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
):
    from sqlalchemy import func

    # Get total count
    total = db.query(func.count(FamilyDocument.id)).filter_by(family_id=current_user.family_id).scalar()

    # Count by type
    report_count = db.query(func.count(FamilyDocument.id)).filter_by(
        family_id=current_user.family_id, type=DocumentType.report
    ).scalar()

    letter_count = db.query(func.count(FamilyDocument.id)).filter_by(
        family_id=current_user.family_id, type=DocumentType.letter
    ).scalar()

    # Count by status "pending"
    pending_count = db.query(func.count(FamilyDocument.id)).filter_by(
        family_id=current_user.family_id, status="pending"
    ).scalar()

    return {
        "total_documents": total,
        "total_reports": report_count,
        "total_letters": letter_count,
        "total_pending": pending_count,
    }


# ========== ADMIN ENDPOINTS ==========

@router.get("/admin/all")
async def admin_list_all_documents(
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_or_pastor_user),
        skip: int = 0,
        limit: Optional[int] = None,
        family_id: Optional[int] = None,
        document_type: Optional[DocumentType] = None,
        status: Optional[str] = None,
        x_total_count: bool = Header(default=False)
):
    """
    Admin endpoint to get all family documents across all families with family details
    """
    # Join with Family table to get family details
    query = db.query(FamilyDocument, Family).join(
        Family, FamilyDocument.family_id == Family.id
    ).order_by(FamilyDocument.uploaded_at.desc())

    # Apply filters
    if family_id:
        query = query.filter(FamilyDocument.family_id == family_id)
    if document_type:
        query = query.filter(FamilyDocument.type == document_type)
    if status:
        query = query.filter(FamilyDocument.status == status)

    # Get total count if requested
    total_count = query.count() if x_total_count else None

    # Apply pagination
    if limit is not None:
        results = query.offset(skip).limit(limit).all()
    else:
        results = query.all()

    # Format response with family details
    documents_with_family = []
    for doc, family in results:
        document_dict = {
            "id": doc.id,
            "family_id": doc.family_id,
            "type": doc.type,
            "original_filename": doc.original_filename,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat(),
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
            "family": {
                "id": family.id,
                "category": family.category,
                "name": family.name,
                "created_at": family.created_at.isoformat(),
                "updated_at": family.updated_at.isoformat()
            }
        }
        documents_with_family.append(document_dict)

    # Include total count in response headers
    headers = {"X-Total-Count": str(total_count)} if total_count is not None else {}

    return JSONResponse(
        content=documents_with_family,
        headers=headers
    )


@router.get("/admin/{doc_id}/download")
def admin_download_document(
        doc_id: int,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_or_pastor_user)
):
    """
    Admin endpoint to download any document by ID (across all families)
    """
    doc = doc_controller.get_admin_document_by_id(db, doc_id)
    return FileResponse(doc.file_path, filename=doc.original_filename)


@router.delete("/admin/{doc_id}")
def admin_delete_document(
        doc_id: int,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_user)
):
    """
    Admin endpoint to delete any document by ID (across all families)
    """
    doc = doc_controller.get_admin_document_by_id(db, doc_id)
    doc_controller.delete_document(db, doc)
    return {"detail": "Document deleted successfully"}


@router.patch("/admin/{doc_id}/status")
def admin_update_document_status(
        doc_id: int,
        status: str = Body(...),
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_or_pastor_user)
):
    """
    Admin endpoint to update document status (only admins can update status)
    """
    doc = doc_controller.get_admin_document_by_id(db, doc_id)

    # Validate allowed statuses per type
    if doc.type == DocumentType.report and status not in [s.value for s in ReportStatus]:
        raise HTTPException(status_code=400, detail="Invalid status for report")
    if doc.type == DocumentType.letter and status not in [s.value for s in LetterStatus]:
        raise HTTPException(status_code=400, detail="Invalid status for letter")

    doc.status = status
    db.commit()
    db.refresh(doc)
    return {"detail": "Status updated successfully", "status": doc.status}


@router.get("/admin/{doc_id}", response_model=DocumentOut)
def admin_get_document(
        doc_id: int,
        db: Session = Depends(get_db),
        current_admin: User = Depends(get_current_admin_or_pastor_user),
):
    """
    Admin endpoint to get any document by ID (across all families)
    """
    return doc_controller.get_admin_document_by_id(db, doc_id)



@router.get("/admin/stats/global")
def admin_global_statistics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_or_pastor_user),
):
    """
    Admin endpoint to get global document statistics across all families
    """
    from sqlalchemy import func

    # Get total count across all families
    total = db.query(func.count(FamilyDocument.id)).scalar()

    # Count by type
    report_count = db.query(func.count(FamilyDocument.id)).filter_by(type=DocumentType.report).scalar()
    letter_count = db.query(func.count(FamilyDocument.id)).filter_by(type=DocumentType.letter).scalar()

    # Count by status
    pending_count = db.query(func.count(FamilyDocument.id)).filter_by(status="pending").scalar()
    approved_count = db.query(func.count(FamilyDocument.id)).filter_by(status="approved").scalar()
    reviewed_count = db.query(func.count(FamilyDocument.id)).filter_by(status="reviewed").scalar()
    submitted_count = db.query(func.count(FamilyDocument.id)).filter_by(status="submitted").scalar()

    # Count by family (top 10 families with most documents) - include family details
    family_stats = db.query(
        Family.id,
        Family.category,
        Family.name,
        func.count(FamilyDocument.id).label('document_count')
    ).join(FamilyDocument, Family.id == FamilyDocument.family_id).group_by(
        Family.id, Family.category, Family.name
    ).order_by(
        func.count(FamilyDocument.id).desc()
    ).limit(10).all()

    return {
        "total_documents": total,
        "total_reports": report_count,
        "total_letters": letter_count,
        "total_pending": pending_count,
        "total_approved": approved_count,
        "total_reviewed": reviewed_count,
        "total_submitted": submitted_count,
        "top_families": [
            {
                "family_id": stat.id,
                "family_category": stat.category,
                "family_name": stat.name,
                "document_count": stat.document_count
            }
            for stat in family_stats
        ]
    }