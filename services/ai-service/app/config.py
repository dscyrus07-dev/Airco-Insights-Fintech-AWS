"""
Configuration settings for AI Intelligence Service.
"""

import os
from typing import List, Optional

class Settings:
    """Application settings."""
    
    # AI Provider Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")
    
    # Processing Settings
    DEFAULT_ANALYSIS_TYPE: str = os.getenv("DEFAULT_ANALYSIS_TYPE", "categorization")
    MAX_TRANSACTIONS_PER_REQUEST: int = int(os.getenv("MAX_TRANSACTIONS_PER_REQUEST", "100"))
    ANALYSIS_TIMEOUT_SECONDS: int = int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "60"))
    
    # RabbitMQ Settings
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672/")
    
    # Redis Settings (for caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Service URLs
    PDF_SERVICE_URL: str = os.getenv("PDF_SERVICE_URL", "http://localhost:8003")
    REPORT_SERVICE_URL: str = os.getenv("REPORT_SERVICE_URL", "http://localhost:8005")
    
    # Service Settings
    SERVICE_NAME: str = "ai-service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Analysis Categories
    DEFAULT_CATEGORIES: List[str] = [
        "Food & Dining",
        "Shopping",
        "Transportation",
        "Bills & Utilities",
        "Entertainment",
        "Healthcare",
        "Education",
        "Travel",
        "Investments",
        "Income",
        "Transfers",
        "Others"
    ]
    
settings = Settings()
