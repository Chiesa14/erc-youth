from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Body, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.models.family_document import FamilyDocument
from app.schemas.family_document import DocumentType, DocumentOut, ReportStatus, LetterStatus
from app.controllers import family_document as doc_controller
from app.core.security import get_db, get_current_active_user
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
