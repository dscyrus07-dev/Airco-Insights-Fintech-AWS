import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import upload as upload
from app.routers import download
from app.api.routes import upload as hdfc_upload
from app.api.routes import upload_async as upload_async_api
from app.api.routes import sync as sync_api
from app.api.routes import feedback as feedback_api
from app.api.routes import jobs as jobs_api
from app.api.routes import profile as profile_api
from app.services.retention_service import retention_service
from app.middleware.correlation import CorrelationMiddleware
from app.utils.logging import get_logger
from contextlib import asynccontextmanager
from app.database.session import initialize_database
from app.database import models as _database_models

logger = get_logger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    initialize_database()

    # Startup
    from app.services.task_processor import task_processor
    from app.services.pdf_processor import register_pdf_processor
    from app.services.message_queue import message_queue
    from app.services.event_consumer import event_consumer
    
    # Register processors
    register_pdf_processor()
    
    # Start RabbitMQ queue bridge
    await message_queue.connect()
    await event_consumer.start_consuming()

    # Start retention sweep worker
    await retention_service.start()

    # Start task processor as a fallback path after RabbitMQ is ready
    await task_processor.start()
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    await retention_service.stop()
    await message_queue.close()
    await task_processor.stop()
    logger.info("Application shutdown complete")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.add_middleware(CorrelationMiddleware)

# API Routes
app.include_router(upload.router, tags=["Processing"])
app.include_router(download.router, tags=["Download"])
app.include_router(hdfc_upload.router, prefix="/api", tags=["HDFC Processing"])
app.include_router(upload_async_api.router, prefix="/api", tags=["Upload Async"])
app.include_router(sync_api.router, prefix="/api", tags=["Sync"])
app.include_router(feedback_api.router, prefix="/api", tags=["Feedback"])
app.include_router(jobs_api.router, prefix="/api", tags=["Jobs"])
app.include_router(profile_api.router, prefix="/api", tags=["Profile"])


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "airco-insights", "version": settings.VERSION}
