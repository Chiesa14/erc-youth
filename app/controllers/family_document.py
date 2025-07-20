import os
import uuid
from sqlalchemy.orm import Session
from app.models.family_document import FamilyDocument
from app.schemas.family_document import DocumentType
from datetime import datetime
from fastapi import UploadFile, HTTPException

UPLOAD_DIR = "uploads/documents"


def save_document_to_disk(family_id: int, file: UploadFile, type: DocumentType) -> str:
    ext = file.filename.split(".")[-1]
    file_id = str(uuid.uuid4())
    filename = f"{file_id}_{type}.{ext}"
    family_dir = os.path.join(UPLOAD_DIR, str(family_id))
    os.makedirs(family_dir, exist_ok=True)
    file_path = os.path.join(family_dir, filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return file_path, filename


def upload_family_document(
        db: Session, family_id: int, type: DocumentType, file: UploadFile
) -> FamilyDocument:
    file_path, filename = save_document_to_disk(family_id, file, type)

    db_doc = FamilyDocument(
        family_id=family_id,
        file_path=file_path,
        type=type.value,
        original_filename=file.filename,
        uploaded_at=datetime.utcnow()
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


def get_document_by_id(db: Session, doc_id: int, family_id: int) -> FamilyDocument:
    doc = db.query(FamilyDocument).filter_by(id=doc_id, family_id=family_id).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def delete_document(db: Session, doc: FamilyDocument):
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()


def list_family_documents(db: Session, family_id: int):
    return db.query(FamilyDocument).filter_by(family_id=family_id).order_by(FamilyDocument.uploaded_at.desc()).all()


