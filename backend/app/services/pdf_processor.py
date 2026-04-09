"""
PDF processing task handler for async processing.
"""

import tempfile
import os
from typing import Dict, Any

from ..models.job import Job, JobType
from ..services.pipeline_orchestrator import process_statement
from ..utils.correlation import get_correlation_id
from ..utils.logging import get_logger

logger = get_logger(__name__)

async def process_pdf_job(job: Job) -> Dict[str, Any]:
    """Process a PDF job asynchronously."""
    logger.info("Starting PDF processing", job_id=job.id)
    
    try:
        # Extract job parameters
        file_path = job.input_data.get("file_path")
        user_info = job.input_data.get("user_info", {})
        mode = job.input_data.get("mode", "free")
        api_key = job.input_data.get("api_key")
        output_dir = job.input_data.get("output_dir")
        
        if not file_path:
            raise ValueError("file_path is required")
        
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        # Create output directory if not provided
        if not output_dir:
            output_dir = os.path.dirname(file_path)
        
        # Process the statement using existing pipeline
        logger.info("Processing statement", job_id=job.id, file_path=file_path)
        result = process_statement(
            file_path=file_path,
            user_info=user_info,
            mode=mode,
            api_key=api_key,
            output_dir=output_dir
        )
        
        # Return result data
        return {
            "status": result.get("status", "success"),
            "excel_path": result.get("excel_path"),
            "stats": result.get("stats", {}),
            "validation": result.get("validation", {}),
            "performance": result.get("performance", {}),
            "bank_key": result.get("bank_key"),
            "mode": result.get("mode")
        }
        
    except Exception as e:
        logger.error("PDF processing failed", job_id=job.id, error=str(e))
        raise

def register_pdf_processor():
    """Register the PDF processor with the task processor."""
    from ..services.task_processor import task_processor
    
    task_processor.register_processor(JobType.PDF_PROCESSING, process_pdf_job)
    logger.info("PDF processor registered")
