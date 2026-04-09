"""
Storage client for Report Generation Service to communicate with MinIO.
"""

import boto3
from typing import Dict, Any, Optional
from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)

class StorageClient:
    """MinIO storage client for report uploads."""
    
    def __init__(self):
        self.config = settings
        self.client = None
    
    def _ensure_client(self):
        if self.client is None:
            self._connect()
    
    def _connect(self):
        """Connect to MinIO."""
        try:
            region_name = getattr(self.config, "MINIO_REGION", "us-east-1")
            self.client = boto3.client(
                's3',
                endpoint_url=self.config.MINIO_ENDPOINT,
                aws_access_key_id=self.config.MINIO_ACCESS_KEY,
                aws_secret_access_key=self.config.MINIO_SECRET_KEY,
                region_name=region_name
            )
            
            # Create bucket if it doesn't exist
            self._ensure_bucket_exists()
            
            logger.info("Connected to MinIO storage", bucket=self.config.MINIO_BUCKET)
            
        except Exception as e:
            logger.error("Failed to connect to MinIO", error=str(e))
            raise
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists."""
        try:
            self.client.head_bucket(Bucket=self.config.MINIO_BUCKET)
        except:
            # Bucket doesn't exist, create it
            self.client.create_bucket(Bucket=self.config.MINIO_BUCKET)
            logger.info("Created MinIO bucket", bucket=self.config.MINIO_BUCKET)
    
    async def upload_file(self, file_path: str, file_name: str, content_type: str) -> Dict[str, Any]:
        """Upload file to MinIO."""
        try:
            self._ensure_client()
            # Upload file
            self.client.upload_file(
                file_path,
                self.config.MINIO_BUCKET,
                file_name,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Generate file URL
            file_url = f"{self.config.MINIO_ENDPOINT}/{self.config.MINIO_BUCKET}/{file_name}"
            
            logger.info("File uploaded to MinIO", file_name=file_name, url=file_url)
            
            return {
                'file_url': file_url,
                'file_name': file_name,
                'bucket': self.config.MINIO_BUCKET
            }
            
        except Exception as e:
            logger.error("Failed to upload file to MinIO", file_name=file_name, error=str(e))
            raise
    
    async def get_file_url(self, file_name: str, expiration: int = 3600) -> Optional[str]:
        """Get presigned URL for file access."""
        try:
            self._ensure_client()
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config.MINIO_BUCKET, 'Key': file_name},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL", file_name=file_name, error=str(e))
            return None

# Global storage client instance
storage_client = StorageClient()
