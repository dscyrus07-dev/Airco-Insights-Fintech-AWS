"""
PDF Processing Service - Standalone PDF parsing and transaction extraction microservice
Handles bank-specific PDF processing and transaction extraction.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes.processing import router as processing_router
from .utils.logging import get_logger
from .middleware.correlation import CorrelationMiddleware

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("PDF Service starting...")
    yield
    logger.info("PDF Service shutdown complete")

app = FastAPI(
    title="Airco PDF Processing Service",
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
app.include_router(processing_router, prefix="/pdf", tags=["pdf-processing"])

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "pdf-service", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Airco PDF Processing Service", "version": "1.0.0"}
