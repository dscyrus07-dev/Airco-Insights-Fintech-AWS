"""
Configuration settings for Report Generation Service.
"""

import os
from typing import List, Optional

class Settings:
    """Application settings."""
    
    # Output Settings
    DEFAULT_REPORT_FORMAT: str = os.getenv("DEFAULT_REPORT_FORMAT", "excel")
    MAX_TRANSACTIONS_PER_REPORT: int = int(os.getenv("MAX_TRANSACTIONS_PER_REPORT", "1000"))
    
    # Storage Settings
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "airco-reports")
    
    # Service URLs
    AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://localhost:8004")
    PDF_SERVICE_URL: str = os.getenv("PDF_SERVICE_URL", "http://localhost:8003")
    
    # RabbitMQ Settings
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/")
    
    # Redis Settings (for caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Service Settings
    SERVICE_NAME: str = "report-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Report Settings
    DEFAULT_SHEETS: List[str] = [
        "Transactions",
        "Summary",
        "Category Analysis",
        "Monthly Trends",
        "Source Analysis",
        "Category Outcome"
    ]
    
    # Template Settings
    TEMPLATE_DIR: str = os.getenv("TEMPLATE_DIR", "app/templates")
    
settings = Settings()
