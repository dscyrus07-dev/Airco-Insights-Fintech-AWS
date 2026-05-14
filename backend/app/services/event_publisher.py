"""
Event publisher for emitting domain events.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .message_queue import message_queue
from ..utils.correlation import get_correlation_id
from ..utils.logging import get_logger

logger = get_logger(__name__)

class EventPublisher:
    """Service for publishing domain events."""
    
    async def publish_file_uploaded(
        self,
        file_id: str,
        filename: str,
        user_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        account_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Publish file uploaded event."""
        event = {
            "event_type": "file_uploaded",
            "event_id": f"file_{file_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": get_correlation_id(),
            "data": {
                "file_id": file_id,
                "filename": filename,
                "user_id": user_id,
                "bank_name": bank_name,
                "account_type": account_type,
                "metadata": metadata or {}
            }
        }
        
        success = await message_queue.publish_message(
            exchange="file_processing",
            routing_key="file.uploaded",
            message=event
        )
        
        if success:
            logger.info("File uploaded event published", file_id=file_id)
        else:
            logger.error("Failed to publish file uploaded event", file_id=file_id)

    async def publish_file_processing_request(
        self,
        job_id: str,
        file_path: str,
        user_info: Dict[str, Any],
        mode: str,
        correlation_id: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_name: Optional[str] = None,
        user_id: Optional[str] = None,
        original_filename: Optional[str] = None,
        upload_object_key: Optional[str] = None,
    ) -> bool:
        """Publish the initial file-processing request event."""
        event = {
            "job_id": job_id,
            "correlation_id": correlation_id or get_correlation_id(),
            "file_path": file_path,
            "user_info": user_info,
            "mode": mode,
            "api_key": api_key,
            "bank_name": bank_name,
            "user_id": user_id,
            "original_filename": original_filename,
            "upload_object_key": upload_object_key,
        }

        success = await message_queue.publish_message(
            exchange="file_processing",
            routing_key="file.uploaded",
            message=event,
        )

        if success:
            logger.info("File processing request published", job_id=job_id)
        else:
            logger.error("Failed to publish file processing request", job_id=job_id)

        return success
    
    async def publish_pdf_processing_request(
        self,
        file_id: str,
        file_url: str,
        bank_name: Optional[str] = None,
        user_id: Optional[str] = None,
        processing_options: Optional[Dict[str, Any]] = None
    ):
        """Publish PDF processing request event."""
        event = {
            "event_type": "pdf_processing_requested",
            "event_id": f"pdf_{file_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": get_correlation_id(),
            "data": {
                "file_id": file_id,
                "file_url": file_url,
                "bank_name": bank_name,
                "user_id": user_id,
                "processing_options": processing_options or {}
            }
        }
        
        success = await message_queue.publish_message(
            exchange="pdf_processing",
            routing_key="pdf.process",
            message=event
        )
        
        if success:
            logger.info("PDF processing event published", file_id=file_id)
        else:
            logger.error("Failed to publish PDF processing event", file_id=file_id)
    
    async def publish_ai_analysis_request(
        self,
        file_id: str,
        transactions: list,
        analysis_type: str = "categorization",
        user_id: Optional[str] = None,
        bank_name: Optional[str] = None
    ):
        """Publish AI analysis request event."""
        event = {
            "event_type": "ai_analysis_requested",
            "event_id": f"ai_{file_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": get_correlation_id(),
            "data": {
                "file_id": file_id,
                "transactions": transactions,
                "analysis_type": analysis_type,
                "user_id": user_id,
                "bank_name": bank_name
            }
        }
        
        success = await message_queue.publish_message(
            exchange="ai_processing",
            routing_key="ai.analyze",
            message=event
        )
        
        if success:
            logger.info("AI analysis event published", file_id=file_id)
        else:
            logger.error("Failed to publish AI analysis event", file_id=file_id)
    
    async def publish_report_generation_request(
        self,
        file_id: str,
        transactions: list,
        ai_results: Optional[Dict[str, Any]] = None,
        report_type: str = "standard",
        user_id: Optional[str] = None,
        bank_name: Optional[str] = None
    ):
        """Publish report generation request event."""
        event = {
            "event_type": "report_generation_requested",
            "event_id": f"report_{file_id}_{datetime.utcnow().timestamp()}",
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": get_correlation_id(),
            "data": {
                "file_id": file_id,
                "transactions": transactions,
                "ai_results": ai_results or {},
                "report_type": report_type,
                "user_id": user_id,
                "bank_name": bank_name
            }
        }
        
        success = await message_queue.publish_message(
            exchange="report_processing",
            routing_key="report.generate",
            message=event
        )
        
        if success:
            logger.info("Report generation event published", file_id=file_id)
        else:
            logger.error("Failed to publish report generation event", file_id=file_id)

# Global event publisher instance
event_publisher = EventPublisher()
