"""
Report Generation Service - Standalone report creation and formatting microservice
Handles Excel report generation with multiple sheets and bank-specific formatting.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes.reports import router as reports_router
from .utils.logging import get_logger
from .middleware.correlation import CorrelationMiddleware

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Report Service starting...")
    yield
    logger.info("Report Service shutdown complete")

app = FastAPI(
    title="Airco Report Generation Service",
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
app.include_router(reports_router, prefix="/reports", tags=["report-generation"])

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "report-service", "version": "1.0.0"}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Airco Report Generation Service", "version": "1.0.0"}
