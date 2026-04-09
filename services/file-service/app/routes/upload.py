"""
File upload routes for File Service.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, List

from ..models.file import (
    FileUploadRequest, FileUploadResponse, 
    FileListResponse, FileStatus
)
from ..services.file_service import file_service
from ..utils.correlation import generate_job_id
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    account_type: Optional[str] = Form(None)
):
    """
    Upload a file to the file service.
    
    Args:
        file: The file to upload
        user_id: Optional user ID
        bank_name: Optional bank name for statements
        account_type: Optional account type
    
    Returns:
        File upload response with file ID and metadata
    """
    try:
        logger.info("File upload started", 
                   filename=file.filename,
                   content_type=file.content_type,
                   user_id=user_id,
                   bank_name=bank_name)
        
        # Upload file
        file_metadata = await file_service.upload_file(
            content=file.file,
            filename=file.filename,
            content_type=file.content_type,
            user_id=user_id,
            bank_name=bank_name,
            account_type=account_type
        )
        
        logger.info("File uploaded successfully", 
                   file_id=file_metadata.id,
                   filename=file.filename)
        
        return FileUploadResponse(
            file_id=file_metadata.id,
            filename=file_metadata.original_filename,
            size_bytes=file_metadata.size_bytes,
            content_type=file_metadata.content_type,
            status=file_metadata.status.value,
            upload_url=file_metadata.storage_url,
            message="File uploaded successfully"
        )
        
    except ValueError as e:
        logger.warning("File validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("File upload failed", error=str(e))
        raise HTTPException(status_code=500, detail="File upload failed")

@router.get("/files", response_model=FileListResponse)
async def list_files(
    user_id: Optional[str] = Query(None),
    status: Optional[FileStatus] = Query(None),
    bank_name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    List files with optional filtering and pagination.
    
    Args:
        user_id: Filter by user ID
        status: Filter by status
        bank_name: Filter by bank name
        page: Page number (1-based)
        page_size: Number of items per page
    
    Returns:
        Paginated list of files
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get files
        files = await file_service.list_files(
            user_id=user_id,
            status=status,
            bank_name=bank_name,
            limit=page_size,
            offset=offset
        )
        
        # Get total count (without pagination for simplicity)
        total_files = await file_service.list_files(
            user_id=user_id,
            status=status,
            bank_name=bank_name,
            limit=10000  # Large limit to get total
        )
        total = len(total_files)
        
        return FileListResponse(
            files=files,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error("Failed to list files", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list files")

@router.get("/files/{file_id}")
async def get_file(file_id: str):
    """
    Get file metadata by ID.
    
    Args:
        file_id: File ID
    
    Returns:
        File metadata
    """
    try:
        file_metadata = await file_service.get_file(file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        return file_metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get file", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get file")

@router.get("/files/{file_id}/download")
async def download_file(file_id: str, expiration: int = Query(3600)):
    """
    Get presigned download URL for a file.
    
    Args:
        file_id: File ID
        expiration: URL expiration time in seconds
    
    Returns:
        Presigned download URL
    """
    try:
        download_url = await file_service.get_download_url(file_id, expiration)
        if not download_url:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"download_url": download_url, "expires_in": expiration}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate download URL", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate download URL")

@router.put("/files/{file_id}/status")
async def update_file_status(
    file_id: str,
    status: FileStatus
):
    """
    Update file status.
    
    Args:
        file_id: File ID
        status: New status
    
    Returns:
        Updated file metadata
    """
    try:
        file_metadata = await file_service.update_file_status(file_id, status)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")
        
        return file_metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update file status", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update file status")

@router.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """
    Delete a file.
    
    Args:
        file_id: File ID
    
    Returns:
        Deletion result
    """
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"message": "File deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete file", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete file")
