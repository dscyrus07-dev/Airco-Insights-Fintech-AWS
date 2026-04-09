"""
Report generation service for creating Excel reports from transactions.
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import tempfile
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import boto3

from ..models.report import (
    ReportGenerationRequest, ReportGenerationResponse,
    ReportStatus, ReportType, ReportFormat, ReportSummary
)
from ..services.bank_report_generators.factory import BankReportGeneratorFactory
from ..services.storage_client import storage_client
from ..utils.logging import get_logger

logger = get_logger(__name__)

class ReportGenerator:
    """Report generation service."""
    
    def __init__(self):
        self.bank_factory = BankReportGeneratorFactory()
        self._report_cache: Dict[str, ReportGenerationResponse] = {}
    
    async def generate_report(self, request: ReportGenerationRequest) -> ReportGenerationResponse:
        """Generate report from transactions."""
        report_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        logger.info("Starting report generation", 
                   report_id=report_id,
                   file_id=request.file_id,
                   bank_name=request.bank_name,
                   report_type=request.report_type.value,
                   transaction_count=len(request.transactions))
        
        try:
            # Create report response
            response = ReportGenerationResponse(
                report_id=report_id,
                file_id=request.file_id,
                status=ReportStatus.GENERATING
            )
            
            # Generate report file
            report_path = await self._create_report_file(request, report_id)
            
            # Upload to storage
            upload_result = await storage_client.upload_file(
                file_path=report_path,
                file_name=f"report_{report_id}.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Calculate processing time
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Generate summary
            summary = self._generate_summary(request.transactions, processing_time)
            
            # Update response
            response.status = ReportStatus.COMPLETED
            response.report_url = upload_result.get('file_url')
            response.download_url = upload_result.get('file_url')
            response.summary = summary
            response.processing_time_seconds = processing_time
            
            logger.info("Report generation completed successfully",
                       report_id=report_id,
                       processing_time=processing_time)
            
            # Cache result
            self._report_cache[report_id] = response
            
            return response
            
        except Exception as e:
            logger.error("Report generation failed",
                        report_id=report_id,
                        error=str(e))
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            response.status = ReportStatus.FAILED
            response.errors.append(str(e))
            response.processing_time_seconds = processing_time
            
            return response
    
    async def _create_report_file(self, request: ReportGenerationRequest, report_id: str) -> str:
        """Create Excel report file."""
        # Get bank-specific report generator
        generator = self.bank_factory.get_generator(request.bank_name.lower())
        
        # Create workbook
        wb = Workbook()
        
        # Remove default sheet
        wb.remove(wb.active)
        
        # Generate sheets based on bank and report type
        sheets = await generator.generate_sheets(
            workbook=wb,
            transactions=request.transactions,
            user_info=request.user_info,
            ai_results=request.ai_results,
            options=request.options
        )
        
        # Save to temporary file
        temp_path = os.path.join(tempfile.gettempdir(), f"report_{report_id}.xlsx")
        wb.save(temp_path)
        
        logger.info("Report file created", report_id=report_id, path=temp_path)
        return temp_path
    
    def _generate_summary(self, transactions: List[Dict[str, Any]], processing_time: float) -> Dict[str, Any]:
        """Generate report summary."""
        if not transactions:
            return {
                "total_transactions": 0,
                "total_credits": 0,
                "total_debits": 0,
                "total_amount": 0.0,
                "date_range": {"start": "", "end": ""},
                "categories": {},
                "monthly_totals": {},
                "average_transaction": 0.0,
                "largest_transaction": {},
                "processing_time_seconds": processing_time
            }
        
        # Calculate totals
        total_transactions = len(transactions)
        credits = [t for t in transactions if t.get('type', '').lower() == 'credit']
        debits = [t for t in transactions if t.get('type', '').lower() == 'debit']
        total_amount = sum(t.get('amount', 0) for t in transactions)
        
        # Date range
        dates = [t.get('date', '') for t in transactions if t.get('date')]
        date_range = {"start": min(dates) if dates else "", "end": max(dates) if dates else ""}
        
        # Categories
        categories = {}
        for txn in transactions:
            cat = txn.get('category', 'Uncategorized')
            categories[cat] = categories.get(cat, 0) + 1
        
        # Monthly totals
        monthly_totals = {}
        for txn in transactions:
            date = txn.get('date', '')
            if date:
                # Extract month (simplified)
                month = date[:7] if len(date) >= 7 else date
                amount = txn.get('amount', 0)
                monthly_totals[month] = monthly_totals.get(month, 0) + amount
        
        # Average and largest transaction
        amounts = [t.get('amount', 0) for t in transactions]
        average_transaction = sum(amounts) / len(amounts) if amounts else 0.0
        
        largest_txn = max(transactions, key=lambda t: t.get('amount', 0)) if transactions else {}
        largest_transaction = {
            "description": largest_txn.get('description', ''),
            "amount": largest_txn.get('amount', 0),
            "date": largest_txn.get('date', '')
        }
        
        return {
            "total_transactions": total_transactions,
            "total_credits": len(credits),
            "total_debits": len(debits),
            "total_amount": total_amount,
            "date_range": date_range,
            "categories": categories,
            "monthly_totals": monthly_totals,
            "average_transaction": average_transaction,
            "largest_transaction": largest_transaction,
            "processing_time_seconds": processing_time
        }
    
    async def get_report_result(self, report_id: str) -> Optional[ReportGenerationResponse]:
        """Get report result by ID."""
        return self._report_cache.get(report_id)
    
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported report formats."""
        return [format.value for format in ReportFormat]
    
    async def get_supported_report_types(self) -> List[str]:
        """Get list of supported report types."""
        return [type.value for type in ReportType]

# Global report generator instance
report_generator = ReportGenerator()
