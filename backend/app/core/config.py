import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Airco Insights Engine"
    VERSION: str = "1.0.0"
    API_PREFIX: str = ""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Anthropic
    ANTHROPIC_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")

    # File handling
    MAX_FILE_SIZE_MB: int = 20
    MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
    ALLOWED_MIME_TYPES: list = ["application/pdf"]
    TEMP_DIR: str = os.getenv("TEMP_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "tmp"))

    # Data retention
    DATA_RETENTION_DAYS: int = int(os.getenv("DATA_RETENTION_DAYS", "7"))
    RETENTION_ENABLED: bool = os.getenv("RETENTION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    RETENTION_SWEEP_INTERVAL_MINUTES: int = int(os.getenv("RETENTION_SWEEP_INTERVAL_MINUTES", "60"))

    # PDF detection
    PDF_TEXT_THRESHOLD: int = 500
    PDF_SCAN_PAGES: int = 3

    # AI classification
    AI_BATCH_SIZE: int = 25

    # Processing
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://test.theairco.ai",
        "https://theairco.ai",
    ]
    
    # Auth Service (for microservices migration)
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
    FILE_SERVICE_URL: str = os.getenv("FILE_SERVICE_URL", "http://localhost:8002")
    PDF_SERVICE_URL: str = os.getenv("PDF_SERVICE_URL", "http://localhost:8003")
    AI_SERVICE_URL: str = os.getenv("AI_SERVICE_URL", "http://localhost:8004")
    REPORT_SERVICE_URL: str = os.getenv("REPORT_SERVICE_URL", "http://localhost:8005")
    
    # Redis (for job storage in Phase 1)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # RabbitMQ (for message queuing in Phase 1)
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "amqp://change-me-rabbitmq-user:change-me-rabbitmq-pass@localhost:5672/")


settings = Settings()
