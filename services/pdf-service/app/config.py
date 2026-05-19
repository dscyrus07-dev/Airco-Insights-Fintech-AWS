"""
Configuration settings for PDF Processing Service.
"""

import os
from typing import List, Optional

class Settings:
    """Application settings."""
    
    # Processing Settings
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
    PROCESSING_TIMEOUT_SECONDS: int = int(os.getenv("PROCESSING_TIMEOUT_SECONDS", "300"))
    
    # Storage Settings
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "airco-files")
    
    # RabbitMQ Settings
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/")
    
    # Redis Settings (for caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # AI Service Settings
    AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://localhost:8004")
    
    # Service Settings
    SERVICE_NAME: str = "pdf-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Supported Banks
    SUPPORTED_BANKS: List[str] = [
        "hdfc",
        "axis",
        "icici",
        "kotak",
        "sbi",
        "canara",
        "idfc",
        "karnataka",
        "paytm",
        "union",
        "bank_of_baroda",
        "unknown",
    ]
    
settings = Settings()
