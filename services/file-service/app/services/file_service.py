"""
File service business logic.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from ..models.file import FileMetadata, FileStatus, FileType
from ..services.storage_service import storage_service
from ..utils.logging import get_logger

logger = get_logger(__name__)

class FileService:
    """File service for managing file uploads and metadata."""
    
    def __init__(self):
        # In-memory file metadata store (will be replaced with database)
        self._files: Dict[str, FileMetadata] = {}
    
    def _validate_file(self, filename: str, content_type: str, size: int) -> None:
        """Validate file before upload."""
        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in [".pdf"]:
            raise ValueError(f"File type {file_ext} not allowed. Only PDF files are accepted.")
        
        # Check MIME type
        if content_type not in ["application/pdf"]:
            raise ValueError(f"Content type {content_type} not allowed.")
        
        # Check file size (20MB limit)
        max_size = 20 * 1024 * 1024  # 20MB in bytes
        if size > max_size:
            raise ValueError(f"File size {size} bytes exceeds maximum allowed size of {max_size} bytes.")
    
    async def upload_file(
        self,
        content,
        filename: str,
        content_type: str,
        user_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        account_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileMetadata:
        """Upload file and create metadata."""
        try:
            # Read content
            file_content = content.read()
            content.seek(0)
            
            # Validate file
            self._validate_file(filename, content_type, len(file_content))
            
            # Upload to storage
            storage_result = await storage_service.upload_file(
                content=content,
                filename=filename,
                content_type=content_type,
                user_id=user_id,
                metadata={
                    'bank_name': bank_name,
                    'account_type': account_type,
                    **(metadata or {})
                }
            )
            
            # Create file metadata
            file_metadata = FileMetadata(
                id=str(uuid.uuid4()),
                original_filename=filename,
                content_type=content_type,
                size_bytes=storage_result['size_bytes'],
                file_type=FileType.PDF,
                status=FileStatus.UPLOADED,
                storage_path=storage_result['file_key'],
                storage_url=storage_result['file_url'],
                checksum=storage_result['checksum'],
                user_id=user_id,
                bank_name=bank_name,
                account_type=account_type,
                metadata=metadata or {}
            )
            
            # Store metadata
            self._files[file_metadata.id] = file_metadata
            
            logger.info("File uploaded successfully", 
                       file_id=file_metadata.id,
                       filename=filename,
                       size_bytes=file_metadata.size_bytes)
            
            return file_metadata
            
        except Exception as e:
            logger.error("Failed to upload file", filename=filename, error=str(e))
            raise
    
    async def get_file(self, file_id: str) -> Optional[FileMetadata]:
        """Get file metadata by ID."""
        return self._files.get(file_id)
    
    async def update_file_status(self, file_id: str, status: FileStatus) -> Optional[FileMetadata]:
        """Update file status."""
        file_metadata = self._files.get(file_id)
        if not file_metadata:
            return None
        
        file_metadata.status = status
        file_metadata.updated_at = datetime.utcnow()
        
        logger.info("File status updated", 
                   file_id=file_id, 
                   status=status.value)
        
        return file_metadata
    
    async def list_files(
        self,
        user_id: Optional[str] = None,
        status: Optional[FileStatus] = None,
        bank_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[FileMetadata]:
        """List files with optional filters."""
        files = list(self._files.values())
        
        # Apply filters
        if user_id:
            files = [f for f in files if f.user_id == user_id]
        
        if status:
            files = [f for f in files if f.status == status]
        
        if bank_name:
            files = [f for f in files if f.bank_name == bank_name]
        
        # Sort by creation date (newest first)
        files.sort(key=lambda f: f.created_at, reverse=True)
        
        # Apply pagination
        return files[offset:offset + limit]
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file and metadata."""
        file_metadata = self._files.get(file_id)
        if not file_metadata:
            return False
        
        try:
            # Delete from storage
            await storage_service.delete_file(file_metadata.storage_path)
            
            # Remove from metadata store
            del self._files[file_id]
            
            logger.info("File deleted successfully", file_id=file_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete file", file_id=file_id, error=str(e))
            return False
    
    async def get_download_url(self, file_id: str, expiration: int = 3600) -> Optional[str]:
        """Get presigned download URL."""
        file_metadata = self._files.get(file_id)
        if not file_metadata:
            return None
        
        return await storage_service.generate_presigned_url(
            file_metadata.storage_path, 
            expiration
        )

# Global file service instance
file_service = FileService()
