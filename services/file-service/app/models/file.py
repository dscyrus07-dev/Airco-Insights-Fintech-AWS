"""
File models for File Service.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class FileStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"

class FileType(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    IMAGE = "image"
    OTHER = "other"

class FileMetadata(BaseModel):
    """File metadata model."""
    id: str = Field(..., description="File ID")
    original_filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    file_type: FileType = Field(..., description="File type")
    status: FileStatus = Field(default=FileStatus.UPLOADED, description="File status")
    storage_path: str = Field(..., description="Storage path")
    storage_url: Optional[str] = Field(None, description="Public URL if accessible")
    checksum: Optional[str] = Field(None, description="File checksum (MD5)")
    user_id: Optional[str] = Field(None, description="User who uploaded the file")
    bank_name: Optional[str] = Field(None, description="Bank name for statements")
    account_type: Optional[str] = Field(None, description="Account type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileUploadRequest(BaseModel):
    """File upload request model."""
    user_id: Optional[str] = None
    bank_name: Optional[str] = None
    account_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FileUploadResponse(BaseModel):
    """File upload response model."""
    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    status: str
    upload_url: Optional[str] = None
    message: str

class FileProcessingEvent(BaseModel):
    """File processing event model."""
    file_id: str
    event_type: str
    status: FileStatus
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class FileListResponse(BaseModel):
    """File list response model."""
    files: list[FileMetadata]
    total: int
    page: int
    page_size: int
