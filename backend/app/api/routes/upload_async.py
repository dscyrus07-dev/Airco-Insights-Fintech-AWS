"""
Async upload endpoints for Phase 1 migration.
Returns job IDs instead of processing synchronously.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import tempfile
import os
from pathlib import Path
from typing import Optional

from ...models.job import Job, JobType, JobStatus
from ...services.redis_job_store import redis_job_store
from ...services.task_processor import task_processor
from ...services.event_publisher import event_publisher
from ...services.file_history_service import file_history_service
from ...dependencies.auth import get_current_user_optional
from ...utils.file_handler import upload_to_minio
from ...utils.correlation import get_correlation_id, generate_job_id
from ...utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/upload", tags=["upload-async"])


def _safe_object_name(filename: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in filename)
    return cleaned.strip("._") or "statement.pdf"

def _extract_user_id_from_request(request: Request) -> Optional[str]:
    forwarded_user_id = request.headers.get("X-Airco-User-Id")
    if forwarded_user_id:
        return forwarded_user_id
    try:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        import jwt as pyjwt
        token = auth.split(" ", 1)[1]
        payload = pyjwt.decode(token, options={"verify_signature": False})
        return payload.get("sub") or payload.get("email") or None
    except Exception:
        return None

async def _save_upload_file(file: UploadFile) -> str:
    """Save uploaded file to temporary location."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 20MB limit")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as pdf_temp:
        pdf_temp.write(content)
        return pdf_temp.name

@router.post("/bank-statement-async")
async def upload_bank_statement_async(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    file: UploadFile = File(...),
    bank_name: str = Form(...),
    full_name: str = Form(default=""),
    account_type: str = Form(default=""),
    mode: str = Form(default="free"),
    api_key: Optional[str] = Form(None),
    batch_id: Optional[str] = Form(None),
    statement_label: Optional[str] = Form(None),
):
    """
    Async upload endpoint that returns a job ID.
    
    Processing happens in background; poll /api/jobs/{job_id} for status.
    """
    logger.info("Async upload received", bank_name=bank_name, filename=file.filename)
    account_type = (account_type or "").strip().lower()
    user_id = (
        (current_user or {}).get("id")
        or request.headers.get("X-Airco-User-Id")
        or _extract_user_id_from_request(request)
        or "anonymous"
    )
    user_email = (current_user or {}).get("email") or request.headers.get("X-Airco-User-Email")
    user_name = (
        (current_user or {}).get("preferred_username")
        or (current_user or {}).get("name")
        or request.headers.get("X-Airco-Preferred-Username")
        or request.headers.get("X-Airco-User-Name")
    )
    full_name = (
        full_name
        or (current_user or {}).get("name")
        or request.headers.get("X-Airco-User-Name")
        or "anonymous"
    )
    
    # Save uploaded file
    file_path = await _save_upload_file(file)
    original_filename = _safe_object_name(file.filename or "statement.pdf")
    upload_object_key = f"users/{user_id}/uploads/{Path(original_filename).stem}_{Path(file_path).name}"
    upload_to_minio(
        file_path,
        bucket="airco-files",
        object_key=upload_object_key,
    )
    
    # Prepare user info
    user_info = {
        "full_name": full_name,
        "account_type": account_type,
        "bank_name": bank_name,
        "batch_id": batch_id,
        "statement_label": statement_label,
    }
    
    # Create job
    job = Job(
        id=generate_job_id(),
        type=JobType.PDF_PROCESSING,
        correlation_id=get_correlation_id(),
        user_id=user_id,
        bank_name=bank_name,
        input_data={
            "file_path": file_path,
            "user_info": user_info,
            "mode": mode,
            "api_key": api_key,
            "original_filename": file.filename,
            "upload_object_key": upload_object_key,
            "batch_id": batch_id,
            "statement_label": statement_label,
        }
    )
    
    # Persist the job first
    job = await redis_job_store.create_job(job)
    file_history_service.upsert_upload(
        job_id=job.id,
        user_id=user_id,
        user_email=user_email,
        user_name=user_name,
        full_name=full_name or None,
        account_type=account_type or None,
        bank_name=bank_name or None,
        batch_id=batch_id,
        statement_label=statement_label,
        mode=mode or None,
        original_filename=file.filename or "statement.pdf",
        upload_object_key=upload_object_key,
    )

    # Prefer RabbitMQ; fall back to the local processor if queue is unavailable
    published = await event_publisher.publish_file_processing_request(
        job_id=job.id,
        file_path=file_path,
        user_info=user_info,
        mode=mode,
        correlation_id=job.correlation_id,
        api_key=api_key,
        bank_name=bank_name,
        user_id=user_id,
        original_filename=file.filename,
        upload_object_key=upload_object_key,
    )

    if not published:
        logger.warning("RabbitMQ publish failed; falling back to local task processor", job_id=job.id)
        job = await task_processor.submit_existing_job(job)
    
    logger.info("Job submitted", job_id=job.id, bank_name=bank_name)
    
    return JSONResponse({
        "job_id": job.id,
        "status": "submitted",
        "message": "Processing started. Check job status with /api/jobs/{job_id}"
    })

@router.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download the processed Excel file when job is complete."""
    job = await redis_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    excel_path = job.result_data.get("excel_path")
    if not excel_path or not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Result file not found")
    
    # Generate filename
    original_filename = job.input_data.get("original_filename", "statement.pdf")
    bank_name = job.bank_name or "unknown"
    output_filename = f"{Path(original_filename).stem}_{bank_name}_report.xlsx"
    
    from fastapi.responses import FileResponse
    return FileResponse(
        excel_path,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=output_filename,
        headers={"Content-Disposition": f"attachment; filename={output_filename}"},
    )
