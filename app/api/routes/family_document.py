from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.schemas.family_document import DocumentType, DocumentOut
from app.controllers import family_document as doc_controller
from app.core.security import get_db, get_current_active_user
from app.models.user import User

router = APIRouter(tags=["Documents"])

@router.get("/", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.family_id:
        raise HTTPException(status_code=400, detail="User has no assigned family")

    return doc_controller.list_family_documents(db, current_user.family_id)


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
