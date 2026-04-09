"""
Configuration settings for File Service.
"""

import os
from typing import List, Optional

class Settings:
    """Application settings."""
    
    # Storage Settings
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "minio")  # minio or s3
    S3_BUCKET: str = os.getenv("S3_BUCKET", "airco-files")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    
    # File Validation
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    ALLOWED_MIME_TYPES: List[str] = ["application/pdf"]
    
    # RabbitMQ Settings
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/")
    RABBITMQ_QUEUE: str = os.getenv("RABBITMQ_QUEUE", "file_processing")
    
    # Redis Settings (for metadata cache)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Service Settings
    SERVICE_NAME: str = "file-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
settings = Settings()
