"""
Report generation routes for Report Generation Service.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List

from ..models.report import (
    ReportGenerationRequest, ReportGenerationResponse, 
    ReportType, ReportFormat, Transaction
)
from ..services.report_generator import report_generator
from ..services.storage_client import storage_client
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a report from transactions.
    
    Args:
        request: Report generation request
        background_tasks: FastAPI background tasks
    
    Returns:
        Report generation response
    """
    try:
        logger.info("Report generation request received", 
                   file_id=request.file_id,
                   bank_name=request.bank_name,
                   report_type=request.report_type.value,
                   transaction_count=len(request.transactions))
        
        # Validate request
        if len(request.transactions) == 0:
            raise HTTPException(status_code=400, detail="No transactions provided")
        
        if len(request.transactions) > 1000:
            raise HTTPException(status_code=400, detail="Too many transactions (max 1000)")
        
        # Normalize transactions to dictionaries for the generator layer
        normalized_transactions = []
        for txn in request.transactions:
            if hasattr(txn, "model_dump"):
                normalized_transactions.append(txn.model_dump())
            else:
                normalized_transactions.append(dict(txn))
        request.transactions = normalized_transactions
        
        # Generate report
        result = await report_generator.generate_report(request)
        
        # If processing is async, add to background tasks
        if result.status.value == "generating":
            background_tasks.add_task(
                _complete_report,
                result.report_id
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Report generation request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Report generation failed")

@router.get("/generate/{report_id}", response_model=ReportGenerationResponse)
async def get_report_result(report_id: str):
    """
    Get report generation result by ID.
    
    Args:
        report_id: Report ID
    
    Returns:
        Report generation result
    """
    try:
        result = await report_generator.get_report_result(report_id)
        if not result:
            raise HTTPException(status_code=404, detail="Report result not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get report result", 
                    report_id=report_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get report result")

@router.get("/formats", response_model=List[str])
async def get_supported_formats():
    """
    Get list of supported report formats.
    
    Returns:
        List of supported report formats
    """
    try:
        formats = await report_generator.get_supported_formats()
        return formats
        
    except Exception as e:
        logger.error("Failed to get supported formats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported formats")

@router.get("/types", response_model=List[str])
async def get_supported_report_types():
    """
    Get list of supported report types.
    
    Returns:
        List of supported report types
    """
    try:
        types = await report_generator.get_supported_report_types()
        return types
        
    except Exception as e:
        logger.error("Failed to get supported report types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported report types")

@router.get("/download/{report_id}")
async def download_report(report_id: str):
    """
    Get download URL for a generated report.
    
    Args:
        report_id: Report ID
    
    Returns:
        Download URL
    """
    try:
        result = await report_generator.get_report_result(report_id)
        if not result:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if result.status.value != "completed":
            raise HTTPException(status_code=400, detail="Report not ready for download")
        
        return {
            "download_url": result.download_url,
            "report_id": report_id,
            "expires_in": 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get download URL", report_id=report_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get download URL")

@router.get("/health/detailed")
async def detailed_health():
    """
    Get detailed health status.
    
    Returns:
        Detailed health status
    """
    return {
        "status": "ok",
        "service": "report-service",
        "version": "1.0.0",
        "storage": {
            "endpoint": storage_client.config.MINIO_ENDPOINT,
            "bucket": storage_client.config.MINIO_BUCKET
        }
    }

async def _complete_report(report_id: str):
    """Background task to complete report generation."""
    # This would be used for async processing
    # For now, processing is synchronous
    pass
