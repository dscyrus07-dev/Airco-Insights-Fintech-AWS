"""
AI Intelligence Service - Standalone AI analysis and categorization microservice
Handles transaction categorization, enrichment, and intelligence analysis.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes.analysis import router as analysis_router
from .utils.logging import get_logger
from .middleware.correlation import CorrelationMiddleware

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("AI Service starting...")
    yield
    logger.info("AI Service shutdown complete")

app = FastAPI(
    title="Airco AI Intelligence Service",
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
app.include_router(analysis_router, prefix="/ai", tags=["ai-analysis"])

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "ai-service", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Airco AI Intelligence Service", "version": "1.0.0"}
