import os
from pathlib import Path
from typing import Optional, List

import boto3
from botocore.client import Config as BotoConfig
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, Response

from ...models.job import Job, JobStatus, JobUpdate
from ...services.redis_job_store import redis_job_store
from ...utils.correlation import get_correlation_id
from ...utils.logging import get_logger
from ...dependencies.auth import get_current_user, get_current_user_optional, get_admin_user, check_user_ownership

logger = get_logger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _ensure_job_access(job: Job, current_user: Optional[dict]) -> None:
    if current_user and not check_user_ownership(job.user_id or "", current_user):
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only view your own jobs"
        )


def _download_from_minio(bucket: str, object_key: str) -> bytes:
    endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )
    response = client.get_object(Bucket=bucket, Key=object_key)
    return response["Body"].read()

@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Get job status and details."""
    job = await redis_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    _ensure_job_access(job, current_user)
    
    return job


@router.get("/{job_id}/download")
async def download_job_result(
    job_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """Download the Excel generated for a completed async job."""
    job = await redis_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    _ensure_job_access(job, current_user)

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    original_filename = job.input_data.get("original_filename", "statement.pdf")
    bank_name = (job.bank_name or "report").replace(" ", "_")
    download_name = f"{Path(original_filename).stem}_{bank_name}_report.xlsx"

    excel_path = job.result_data.get("excel_path")
    if excel_path and os.path.isfile(excel_path):
        return FileResponse(
            path=excel_path,
            filename=download_name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    excel_object_key = job.result_data.get("excel_object_key")
    if excel_object_key:
        try:
            content = _download_from_minio("airco-reports", excel_object_key)
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
            )
        except Exception as e:
            logger.error("MinIO download failed", job_id=job_id, object_key=excel_object_key, error=str(e))

    raise HTTPException(status_code=404, detail="Result file not found")

@router.get("/", response_model=List[Job])
async def list_jobs(
    current_user: dict = Depends(get_current_user),
    status: Optional[JobStatus] = None
):
    """List jobs for the current user."""
    jobs = []
    
    # Get all jobs and filter by user ownership
    all_jobs = await redis_job_store.list_jobs()
    
    for job in all_jobs:
        # Admin can see all jobs, users can only see their own
        if check_user_ownership(job.user_id or "", current_user):
            if status is None or job.status == status:
                jobs.append(job)
    
    return jobs

# Admin-only endpoints
@router.get("/admin/all", response_model=List[Job])
async def list_all_jobs(
    current_user: dict = Depends(get_admin_user),
    status: Optional[JobStatus] = None
):
    """List all jobs (admin only)."""
    jobs = await redis_job_store.list_jobs()
    
    if status is not None:
        jobs = [job for job in jobs if job.status == status]
    
    return jobs

@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a job."""
    job = await redis_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not check_user_ownership(job.user_id or "", current_user):
        raise HTTPException(
            status_code=403, 
            detail="Access denied: You can only delete your own jobs"
        )
    
    # Only allow deletion of completed or failed jobs
    if job.status not in [JobStatus.COMPLETED, JobStatus.FAILED]:
        raise HTTPException(
            status_code=400, 
            detail="Can only delete completed or failed jobs"
        )
    
    await redis_job_store.delete_job(job_id)
    return {"message": "Job deleted successfully"}

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Cancel a running job."""
    job = await redis_job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check ownership
    if not check_user_ownership(job.user_id or "", current_user):
        raise HTTPException(
            status_code=403, 
            detail="Access denied: You can only cancel your own jobs"
        )
    
    # Only allow cancellation of running jobs
    if job.status != JobStatus.RUNNING:
        raise HTTPException(
            status_code=400, 
            detail="Can only cancel running jobs"
        )
    
    await redis_job_store.update_job_status(job_id, JobStatus.CANCELLED)
    logger.info("Job cancelled", job_id=job_id, correlation_id=get_correlation_id())
    return {"message": "Job cancelled successfully"}
