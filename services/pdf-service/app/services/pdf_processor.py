"""
PDF processing service for extracting transactions from bank statements.
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import tempfile
import os
import httpx

from ..models.pdf import (
    PDFProcessingRequest, PDFProcessingResponse, 
    ProcessingStatus, Transaction, ProcessingSummary
)
from ..services.bank_processors.factory import BankProcessorFactory
from ..services.storage_client import storage_client
from ..utils.logging import get_logger

logger = get_logger(__name__)

class PDFProcessor:
    """PDF processing service."""
    
    def __init__(self):
        self.bank_factory = BankProcessorFactory()
        self._processing_cache: Dict[str, PDFProcessingResponse] = {}
    
    async def process_pdf(self, request: PDFProcessingRequest) -> PDFProcessingResponse:
        """Process PDF file and extract transactions."""
        processing_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info("Starting PDF processing", 
                   processing_id=processing_id,
                   file_id=request.file_id,
                   bank_name=request.bank_name.value)
        
        try:
            # Create processing response
            response = PDFProcessingResponse(
                processing_id=processing_id,
                file_id=request.file_id,
                status=ProcessingStatus.PROCESSING
            )
            
            # Download file from storage
            file_content = await storage_client.download_file(request.file_url)
            if not file_content:
                response.status = ProcessingStatus.FAILED
                response.errors.append("Failed to download file from storage")
                return response
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name
            
            try:
                # Get bank processor
                processor = self.bank_factory.get_processor(request.bank_name.value)
                
                # Process PDF
                logger.info("Processing PDF with bank processor", 
                           processing_id=processing_id,
                           bank=request.bank_name.value)
                
                result = await processor.process_pdf(temp_path, request.processing_options)
                
                # Extract transactions
                transactions = []
                for txn_data in result.get('transactions', []):
                    transaction = Transaction(
                        date=txn_data.get('date', ''),
                        description=txn_data.get('description', ''),
                        amount=txn_data.get('amount', 0.0),
                        type=txn_data.get('type', 'unknown'),
                        balance=txn_data.get('balance'),
                        category=txn_data.get('category'),
                        metadata=txn_data.get('metadata', {})
                    )
                    transactions.append(transaction)
                
                # Calculate processing time
                end_time = datetime.utcnow()
                processing_time = (end_time - start_time).total_seconds()
                
                # Generate summary
                summary = self._generate_summary(transactions, processing_time)
                
                # Update response
                response.status = ProcessingStatus.COMPLETED
                response.transactions = transactions
                response.summary = summary
                response.processing_time_seconds = processing_time
                
                logger.info("PDF processing completed successfully",
                           processing_id=processing_id,
                           transaction_count=len(transactions),
                           processing_time=processing_time)
                
                # Cache result
                self._processing_cache[processing_id] = response
                
                return response
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
        except Exception as e:
            logger.error("PDF processing failed",
                        processing_id=processing_id,
                        error=str(e))
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            response.status = ProcessingStatus.FAILED
            response.errors.append(str(e))
            response.processing_time_seconds = processing_time
            
            return response
    
    def _generate_summary(self, transactions: List[Transaction], processing_time: float) -> Dict[str, Any]:
        """Generate processing summary."""
        if not transactions:
            return {
                "total_transactions": 0,
                "total_credits": 0,
                "total_debits": 0,
                "total_amount": 0.0,
                "date_range": {"start": "", "end": ""},
                "categories": {},
                "processing_time_seconds": processing_time
            }
        
        # Calculate totals
        total_transactions = len(transactions)
        credits = [t for t in transactions if t.type.lower() == 'credit']
        debits = [t for t in transactions if t.type.lower() == 'debit']
        total_amount = sum(t.amount for t in transactions)
        
        # Date range
        dates = [t.date for t in transactions if t.date]
        date_range = {"start": min(dates) if dates else "", "end": max(dates) if dates else ""}
        
        # Categories
        categories = {}
        for txn in transactions:
            if txn.category:
                categories[txn.category] = categories.get(txn.category, 0) + 1
        
        return {
            "total_transactions": total_transactions,
            "total_credits": len(credits),
            "total_debits": len(debits),
            "total_amount": total_amount,
            "date_range": date_range,
            "categories": categories,
            "processing_time_seconds": processing_time
        }
    
    async def get_processing_result(self, processing_id: str) -> Optional[PDFProcessingResponse]:
        """Get processing result by ID."""
        return self._processing_cache.get(processing_id)
    
    async def get_supported_banks(self) -> List[str]:
        """Get list of supported banks."""
        return self.bank_factory.get_supported_banks()

# Global PDF processor instance
pdf_processor = PDFProcessor()
