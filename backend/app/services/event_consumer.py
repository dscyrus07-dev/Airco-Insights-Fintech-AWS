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
from ..utils.file_handler import cleanup_file, upload_to_minio, download_from_minio
from ..models.job import JobStatus, JobUpdate
from ..utils.correlation import set_correlation_id
from ..utils.logging import get_logger
from ..database.session import get_db
from .audit.audit_service import AuditService
from ..database.audit_models import ProcessingJob

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

        upload_object_key = payload.get("upload_object_key")
        user_info = payload.get("user_info", {})
        mode = payload.get("mode", "free")
        api_key = payload.get("api_key")
        user_id = payload.get("user_id") or "anonymous"
        original_filename = payload.get("original_filename") or "statement.pdf"
        output_dir = payload.get("output_dir")

        if not job_id:
            logger.warning("file_upload event missing job_id; skipping job update")
            return True

        if not upload_object_key:
            raise ValueError("upload_object_key is required in queue payload")

        # Download file from MinIO to local temp
        file_path = download_from_minio(
            bucket="airco-files",
            object_key=upload_object_key,
        )

        if not file_path or not os.path.isfile(file_path):
            raise ValueError(f"Failed to download file from MinIO: {upload_object_key}")

        if not output_dir:
            output_dir = os.path.dirname(file_path)

        # Bootstrap audit service for Supabase logging
        audit_service = None
        audit_db = None
        try:
            from ..database.session import SessionLocal
            audit_db = SessionLocal()
            audit_service = AuditService(audit_db)
            import hashlib as _hl, os as _os
            file_hash = _hl.sha256(open(file_path, 'rb').read()).hexdigest()
            file_size = _os.path.getsize(file_path)
            audit_service.create_processing_job(
                tenant_id="default",
                user_id=user_id,
                job_id=job_id,
                original_filename=original_filename,
                file_hash=file_hash,
                file_size_bytes=file_size,
                processing_mode=mode.upper(),
            )
        except Exception as ae:
            logger.warning("Audit job creation failed (non-fatal)", job_id=job_id, error=str(ae))
            # Keep audit_service alive even if job creation failed — finalize_job_audit uses its own fresh session
            if audit_db is None:
                try:
                    from ..database.session import SessionLocal
                    audit_db = SessionLocal()
                    audit_service = AuditService(audit_db)
                except Exception:
                    audit_service = None
                    audit_db = None

        try:
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
                audit_service=audit_service,
                job_id=job_id,
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
                result["source_pdf_object_key"] = upload_object_key
            frontend_result = build_frontend_processing_result(
                result,
                mode=mode,
                excel_url=f"/api/jobs/{job_id}/download",
            )
            await self._mark_job(job_id, JobStatus.COMPLETED, result_data=frontend_result)
            # Always use a fresh session for audit status update to avoid poisoned transactions
            try:
                from ..database.session import SessionLocal
                fresh_db = SessionLocal()
                fresh_audit = AuditService(fresh_db)
                txn_count = result.get("stats", {}).get("total_transactions", 0)
                parser_used = result.get("performance", {}).get("parser_used", "unknown")
                processing_ms = int(result.get("performance", {}).get("total_time_ms", 0))
                fresh_audit.update_processing_job(
                    job_id=job_id,
                    status="COMPLETED",
                    bank_name=user_info.get("bank_name", ""),
                    transaction_count=txn_count,
                    parser_used=parser_used,
                    processing_time_ms=processing_ms,
                )
                fresh_db.close()
                logger.info("Audit job updated to COMPLETED", job_id=job_id, bank_name=user_info.get("bank_name", ""))
            except Exception as ue:
                logger.error("Audit job update failed", job_id=job_id, error=str(ue))
            try:
                file_history_service.mark_completed(job_id, frontend_result)
            except Exception as e:
                logger.warning("Failed to update file history service for completed status", job_id=job_id, error=str(e))
            logger.info("Queued statement processed", job_id=job_id, bank_name=user_info.get("bank_name"))
            return True
        except Exception as e:
            logger.error("Queued statement processing failed", job_id=job_id, error=str(e))
            # Always use a fresh session for audit status update
            try:
                from ..database.session import SessionLocal
                fresh_db = SessionLocal()
                fresh_audit = AuditService(fresh_db)
                fresh_audit.update_processing_job(job_id=job_id, status="FAILED", error_message=str(e))
                fresh_db.close()
                logger.info("Audit job updated to FAILED", job_id=job_id)
            except Exception as fe:
                logger.error("Failed to update audit job to FAILED status", job_id=job_id, error=str(fe))
            await self._mark_job(job_id, JobStatus.FAILED, error_message=str(e))
            try:
                file_history_service.mark_failed(job_id, str(e))
            except Exception as fe:
                logger.warning("Failed to update file history service for failed status", job_id=job_id, error=str(fe))
            return False
        finally:
            cleanup_file(file_path)
            # Clean up audit database session
            if audit_db:
                try:
                    audit_db.close()
                except Exception:
                    pass

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
