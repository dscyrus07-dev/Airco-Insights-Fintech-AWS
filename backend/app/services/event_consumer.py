"""
Event consumer for processing domain events.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from .message_queue import message_queue
from .pipeline_orchestrator import process_statement
from .redis_job_store import redis_job_store
from .file_history_service import file_history_service
from .frontend_result_builder import build_frontend_processing_result
from ..utils.file_handler import upload_to_minio
from ..models.job import JobStatus, JobUpdate
from ..utils.correlation import set_correlation_id
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _safe_object_name(filename: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in filename)
    return cleaned.strip("._") or "statement.pdf"


class EventConsumer:
    """Consumes RabbitMQ events and bridges them into the existing bank pipeline."""

    def __init__(self):
        self._register_handlers()

    def _register_handlers(self):
        message_queue.register_consumer("file_upload_queue", self._handle_file_uploaded)
        message_queue.register_consumer("pdf_processing_queue", self._handle_pipeline_result)
        message_queue.register_consumer("ai_analysis_queue", self._handle_pipeline_result)
        message_queue.register_consumer("report_generation_queue", self._handle_pipeline_result)

    async def _mark_job(self, job_id: str, status: JobStatus, result_data: Dict[str, Any] | None = None, error_message: str | None = None):
        update = JobUpdate(status=status, result_data=result_data, error_message=error_message)
        await redis_job_store.update_job(job_id, update)

    async def _handle_file_uploaded(self, payload: Dict[str, Any]):
        """Process a file upload event using the existing deterministic bank pipeline."""
        job_id = payload.get("job_id")
        correlation_id = payload.get("correlation_id")
        if correlation_id:
            set_correlation_id(correlation_id)

        file_path = payload.get("file_path")
        user_info = payload.get("user_info", {})
        mode = payload.get("mode", "free")
        api_key = payload.get("api_key")
        user_id = payload.get("user_id") or "anonymous"
        original_filename = payload.get("original_filename") or "statement.pdf"
        output_dir = payload.get("output_dir") or (os.path.dirname(file_path) if file_path else None)

        if not job_id:
            logger.warning("file_upload event missing job_id; skipping job update")
            return True

        try:
            if not file_path:
                raise ValueError("file_path is required in queue payload")

            await self._mark_job(job_id, JobStatus.RUNNING)
            try:
                file_history_service.mark_running(job_id)
            except Exception as e:
                logger.warning("Failed to update file history service for running status", job_id=job_id, error=str(e))
            result = process_statement(
                file_path=file_path,
                user_info=user_info,
                mode=mode,
                api_key=api_key,
                output_dir=output_dir,
            )
            excel_path = result.get("excel_path")
            if excel_path and os.path.isfile(excel_path):
                safe_original = _safe_object_name(original_filename)
                excel_object_key = f"users/{user_id}/reports/{Path(excel_path).name}"
                upload_to_minio(
                    excel_path,
                    bucket="airco-reports",
                    object_key=excel_object_key,
                )
                result["excel_object_key"] = excel_object_key
                result["source_pdf_object_key"] = payload.get("upload_object_key") or (
                    f"users/{user_id}/uploads/{Path(safe_original).stem}_{Path(file_path).name}"
                )
            frontend_result = build_frontend_processing_result(
                result,
                mode=mode,
                excel_url=f"/api/jobs/{job_id}/download",
            )
            await self._mark_job(job_id, JobStatus.COMPLETED, result_data=frontend_result)
            try:
                file_history_service.mark_completed(job_id, frontend_result)
            except Exception as e:
                logger.warning("Failed to update file history service for completed status", job_id=job_id, error=str(e))
            logger.info("Queued statement processed", job_id=job_id, bank_name=user_info.get("bank_name"))
            return True
        except Exception as e:
            logger.error("Queued statement processing failed", job_id=job_id, error=str(e))
            await self._mark_job(job_id, JobStatus.FAILED, error_message=str(e))
            try:
                file_history_service.mark_failed(job_id, str(e))
            except Exception as fe:
                logger.warning("Failed to update file history service for failed status", job_id=job_id, error=str(fe))
            return False

    async def _handle_pipeline_result(self, payload: Dict[str, Any]):
        """Compatibility handler for downstream queues."""
        job_id = payload.get("job_id")
        correlation_id = payload.get("correlation_id")
        if correlation_id:
            set_correlation_id(correlation_id)

        if not job_id:
            return True

        status = payload.get("status", "completed").lower()
        result_data = payload.get("result_data") or payload.get("data") or {}
        error_message = payload.get("error_message")

        if status in {"failed", "error"}:
            await self._mark_job(job_id, JobStatus.FAILED, result_data=result_data, error_message=error_message or "Pipeline event failed")
        else:
            await self._mark_job(job_id, JobStatus.COMPLETED, result_data=result_data)
        return True

    async def start_consuming(self):
        await message_queue.start_consuming()


event_consumer = EventConsumer()
