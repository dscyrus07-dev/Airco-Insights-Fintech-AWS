"""
File Ingestion Service - Standalone file upload and storage microservice
Handles file validation, storage, and metadata management.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes.upload import router as upload_router
from .utils.logging import get_logger
from .middleware.correlation import CorrelationMiddleware

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("File Service starting...")
    yield
    logger.info("File Service shutdown complete")

app = FastAPI(
    title="Airco File Service",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware
app.add_middleware(CorrelationMiddleware)

# Include routes
app.include_router(upload_router, prefix="/files", tags=["file-upload"])

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "file-service", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Airco File Service", "version": "1.0.0"}
