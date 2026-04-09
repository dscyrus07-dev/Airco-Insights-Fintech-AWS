"""
PDF processing routes for PDF Processing Service.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List

from ..models.pdf import (
    PDFProcessingRequest, PDFProcessingResponse, 
    ProcessingStatus, BankType
)
from ..services.pdf_processor import pdf_processor
from ..utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/process", response_model=PDFProcessingResponse)
async def process_pdf(
    request: PDFProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a PDF file and extract transactions.
    
    Args:
        request: PDF processing request
        background_tasks: FastAPI background tasks
    
    Returns:
        PDF processing response with transactions
    """
    try:
        logger.info("PDF processing request received", 
                   file_id=request.file_id,
                   bank_name=request.bank_name.value)
        
        # Process PDF
        result = await pdf_processor.process_pdf(request)
        
        # If processing is async, add to background tasks
        if result.status == ProcessingStatus.PROCESSING:
            background_tasks.add_task(
                _complete_processing,
                result.processing_id
            )
        
        return result
        
    except Exception as e:
        logger.error("PDF processing request failed", error=str(e))
        raise HTTPException(status_code=500, detail="PDF processing failed")

@router.get("/process/{processing_id}", response_model=PDFProcessingResponse)
async def get_processing_result(processing_id: str):
    """
    Get PDF processing result by ID.
    
    Args:
        processing_id: Processing ID
    
    Returns:
        PDF processing result
    """
    try:
        result = await pdf_processor.get_processing_result(processing_id)
        if not result:
            raise HTTPException(status_code=404, detail="Processing result not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get processing result", 
                    processing_id=processing_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get processing result")

@router.get("/banks", response_model=List[str])
async def get_supported_banks():
    """
    Get list of supported banks.
    
    Returns:
        List of supported bank names
    """
    try:
        banks = await pdf_processor.get_supported_banks()
        return banks
        
    except Exception as e:
        logger.error("Failed to get supported banks", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported banks")

@router.post("/validate")
async def validate_pdf_bank(
    file_url: str,
    bank_name: BankType
):
    """
    Validate if PDF is from specified bank.
    
    Args:
        file_url: URL of the PDF file
        bank_name: Expected bank name
    
    Returns:
        Validation result
    """
    try:
        # Download file
        from ..services.storage_client import storage_client
        file_content = await storage_client.download_file(file_url)
        
        if not file_content:
            raise HTTPException(status_code=400, detail="Failed to download file")
        
        # Save to temporary file
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        try:
            # Get bank processor
            processor = pdf_processor.bank_factory.get_processor(bank_name.value)
            
            # Validate PDF
            is_valid = processor.validate_pdf(temp_path)
            
            return {
                "valid": is_valid,
                "bank": bank_name.value,
                "message": "PDF is from specified bank" if is_valid else "PDF is not from specified bank"
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("PDF validation failed", error=str(e))
        raise HTTPException(status_code=500, detail="PDF validation failed")

async def _complete_processing(processing_id: str):
    """Background task to complete processing."""
    # This would be used for async processing
    # For now, processing is synchronous
    pass
