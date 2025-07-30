from pydantic import BaseModel, computed_field
from datetime import datetime
from typing import Optional


class SharedDocumentBase(BaseModel):
    name: str
    size: int


class SharedDocumentCreate(BaseModel):
    # For file uploads, we don't need name and size in the request
    # as they'll be extracted from the uploaded file
    pass


class SharedDocumentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class SharedDocumentOut(SharedDocumentBase):
    id: int
    original_filename: str
    mime_type: Optional[str] = None
    description: Optional[str] = None
    uploaded_at: datetime
    downloads: int
    is_public: bool
    uploaded_by: Optional[int] = None

    @computed_field
    @property
    def is_flyer(self) -> bool:
        """Computed field to check if document is a flyer"""
        # This will be set by the controller based on announcement relationship
        return getattr(self, '_is_flyer', False)

    class Config:
        from_attributes = True


class SharedDocumentList(BaseModel):
    documents: list[SharedDocumentOut]
    total: int
    page: int
    per_page: int
    total_pages: int


class DocumentStats(BaseModel):
    total_documents: int
    total_downloads: int
    recent_uploads: int
    flyers: Optional[int] = None
    standalone_documents: Optional[int] = None
    types: list[dict]