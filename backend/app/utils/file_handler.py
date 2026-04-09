import os
import uuid
import logging
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_temp_dir() -> str:
    """Get or create temporary directory for file processing."""
    temp_dir = os.path.abspath(settings.TEMP_DIR)
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def save_temp_file(content: bytes, extension: str = ".pdf") -> str:
    """Save bytes content to a uniquely named temp file. Returns file path."""
    temp_dir = get_temp_dir()
    filename = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"Temp file saved: {filename} ({len(content)} bytes)")
    return file_path


def cleanup_file(file_path: str) -> None:
    """Safely delete a file."""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up: {os.path.basename(file_path)}")
    except OSError as e:
        logger.warning(f"Failed to clean up {file_path}: {e}")


def cleanup_files(*file_paths: str) -> None:
    """Safely delete multiple files."""
    for path in file_paths:
        if path:
            cleanup_file(path)


def upload_to_minio(local_path: str, bucket: str, object_key: str = None) -> bool:
    """
    Upload a local file to a MinIO bucket.
    Returns True on success, False on any failure (non-blocking).
    """
    try:
        import boto3
        from botocore.client import Config as BotoConfig

        endpoint   = os.getenv("MINIO_ENDPOINT",   "http://minio:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY",  "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY",  "minioadmin")

        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=BotoConfig(signature_version="s3v4"),
            region_name="us-east-1",
        )

        # Auto-create bucket if it doesn't exist
        try:
            client.head_bucket(Bucket=bucket)
        except Exception:
            client.create_bucket(Bucket=bucket)
            logger.info("Created MinIO bucket: %s", bucket)

        if object_key is None:
            object_key = os.path.basename(local_path)

        _, ext = os.path.splitext(local_path)
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if ext.lower() == ".xlsx"
            else "application/pdf"
        )

        client.upload_file(
            local_path, bucket, object_key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info("MinIO upload OK: %s → %s/%s", local_path, bucket, object_key)
        return True

    except Exception as e:
        logger.warning("MinIO upload failed (non-fatal): %s", str(e))
        return False
