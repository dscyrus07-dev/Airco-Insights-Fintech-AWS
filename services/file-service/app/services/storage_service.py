"""
Storage service for S3/MinIO integration.
"""

import hashlib
import uuid
from typing import Optional, BinaryIO
from urllib.parse import urljoin
import boto3
from botocore.exceptions import ClientError

from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)

class StorageService:
    """S3/MinIO storage service."""
    
    def __init__(self):
        self.config = settings
        self.client = None
    
    def _ensure_client(self):
        if self.client is None:
            self._connect()
    
    def _connect(self):
        """Connect to S3/MinIO."""
        try:
            self.client = boto3.client(
                's3',
                endpoint_url=self.config.S3_ENDPOINT,
                aws_access_key_id=self.config.S3_ACCESS_KEY,
                aws_secret_access_key=self.config.S3_SECRET_KEY,
                region_name=self.config.S3_REGION
            )
            
            # Create bucket if it doesn't exist
            self._ensure_bucket_exists()
            
            logger.info("Connected to storage service", bucket=self.config.S3_BUCKET)
            
        except Exception as e:
            logger.error("Failed to connect to storage service", error=str(e))
            raise
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists."""
        try:
            self.client.head_bucket(Bucket=self.config.S3_BUCKET)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket doesn't exist, create it
                self.client.create_bucket(Bucket=self.config.S3_BUCKET)
                logger.info("Created bucket", bucket=self.config.S3_BUCKET)
            else:
                raise
    
    def generate_file_key(self, filename: str, user_id: Optional[str] = None) -> str:
        """Generate a unique file key for storage."""
        # Extract file extension
        file_ext = filename.split('.')[-1] if '.' in filename else ''
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())
        
        # Build key path
        if user_id:
            key = f"users/{user_id}/{unique_id}.{file_ext}"
        else:
            key = f"uploads/{unique_id}.{file_ext}"
        
        return key
    
    def calculate_checksum(self, content: bytes) -> str:
        """Calculate MD5 checksum of file content."""
        return hashlib.md5(content).hexdigest()
    
    async def upload_file(
        self,
        content: BinaryIO,
        filename: str,
        content_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> dict:
        """Upload file to storage."""
        try:
            self._ensure_client()
            # Read content
            file_content = content.read()
            content.seek(0)  # Reset file pointer
            
            # Calculate checksum
            checksum = self.calculate_checksum(file_content)
            
            # Generate file key
            file_key = self.generate_file_key(filename, user_id)
            
            # Prepare metadata
            s3_metadata = {
                'original_filename': filename,
                'content_type': content_type,
                'checksum': checksum,
                'user_id': user_id or 'anonymous',
                **(metadata or {})
            }
            
            # Upload to S3/MinIO
            self.client.put_object(
                Bucket=self.config.S3_BUCKET,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=s3_metadata
            )
            
            # Generate URL
            file_url = self._get_file_url(file_key)
            
            logger.info("File uploaded successfully", 
                       file_key=file_key, 
                       size=len(file_content),
                       checksum=checksum)
            
            return {
                'file_key': file_key,
                'file_url': file_url,
                'checksum': checksum,
                'size_bytes': len(file_content)
            }
            
        except Exception as e:
            logger.error("Failed to upload file", error=str(e))
            raise
    
    def _get_file_url(self, file_key: str) -> str:
        """Get file URL."""
        if self.config.STORAGE_TYPE == "minio":
            # MinIO URL format
            return urljoin(self.config.S3_ENDPOINT, f"/{self.config.S3_BUCKET}/{file_key}")
        else:
            # S3 URL format (if public bucket)
            return f"https://{self.config.S3_BUCKET}.s3.{self.config.S3_REGION}.amazonaws.com/{file_key}"
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete file from storage."""
        try:
            self._ensure_client()
            self.client.delete_object(Bucket=self.config.S3_BUCKET, Key=file_key)
            logger.info("File deleted successfully", file_key=file_key)
            return True
        except Exception as e:
            logger.error("Failed to delete file", file_key=file_key, error=str(e))
            return False
    
    async def get_file_metadata(self, file_key: str) -> Optional[dict]:
        """Get file metadata from storage."""
        try:
            self._ensure_client()
            response = self.client.head_object(Bucket=self.config.S3_BUCKET, Key=file_key)
            return {
                'content_length': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {}),
                'etag': response.get('ETag', '').strip('"')
            }
        except Exception as e:
            logger.error("Failed to get file metadata", file_key=file_key, error=str(e))
            return None
    
    async def generate_presigned_url(self, file_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for file access."""
        try:
            self._ensure_client()
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.config.S3_BUCKET, 'Key': file_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error("Failed to generate presigned URL", file_key=file_key, error=str(e))
            return None

# Global storage service instance
storage_service = StorageService()
