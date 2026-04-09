"""
Storage client for PDF Processing Service to communicate with File Service.
"""

import httpx
from typing import Optional
from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)

class StorageClient:
    """Client for communicating with File Service."""
    
    def __init__(self):
        self.base_url = settings.MINIO_ENDPOINT
        self.timeout = 30.0
    
    async def download_file(self, file_url: str) -> Optional[bytes]:
        """Download file from storage."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(file_url)
                if response.status_code == 200:
                    logger.info("File downloaded successfully", url=file_url)
                    return response.content
                else:
                    logger.error("Failed to download file", 
                               url=file_url, 
                               status=response.status_code)
                    return None
                    
        except Exception as e:
            logger.error("Error downloading file", url=file_url, error=str(e))
            return None
    
    async def get_file_metadata(self, file_id: str) -> Optional[dict]:
        """Get file metadata from File Service."""
        try:
            # This would call the File Service API
            # For now, return None as placeholder
            return None
        except Exception as e:
            logger.error("Error getting file metadata", file_id=file_id, error=str(e))
            return None

# Global storage client instance
storage_client = StorageClient()
