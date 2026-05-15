"""
Redis-based job store for Phase 1.
Replaces in-memory job store with Redis for persistence.
"""

import json
import pickle
from typing import Dict, Optional, List
from datetime import datetime
import redis.asyncio as redis

from ..models.job import Job, JobStatus, JobUpdate
from ..core.config import settings
from ..utils.logging import get_logger
from .job_store import job_store as fallback_job_store

logger = get_logger(__name__)

class RedisJobStore:
    """Redis-based job storage."""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.key_prefix = "airco:job:"
    
    def _client(self) -> redis.Redis:
        return redis.from_url(self.redis_url, decode_responses=False)

    async def _redis_available(self) -> bool:
        client = self._client()
        try:
            await client.ping()
            return True
        except Exception as exc:
            logger.warning("Redis unavailable; using in-memory job store fallback", error=str(exc))
            return False
        finally:
            try:
                await client.aclose()
            except Exception:
                pass
    
    async def disconnect(self):
        """Disconnect from Redis."""
        # Clients are created per operation and closed immediately.
        return None
    
    async def create_job(self, job: Job) -> Job:
        """Create a new job in Redis."""
        if not await self._redis_available():
            return await fallback_job_store.create_job(job)

        client = self._client()
        try:
            await client.ping()

            # Serialize job
            job_data = pickle.dumps(job)

            # Store in Redis with TTL (24 hours)
            await client.setex(
                f"{self.key_prefix}{job.id}",
                86400,  # 24 hours TTL
                job_data
            )

            # Add to user's job list
            if job.user_id:
                await client.sadd(f"{self.key_prefix}user:{job.user_id}", job.id)

            # Add to status index
            await client.sadd(f"{self.key_prefix}status:{job.status.value}", job.id)

            logger.info("Job created in Redis", job_id=job.id, job_type=job.type)
            return job
        finally:
            await client.aclose()
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID from Redis."""
        if not await self._redis_available():
            return await fallback_job_store.get_job(job_id)

        client = self._client()
        try:
            await client.ping()
            job_data = await client.get(f"{self.key_prefix}{job_id}")
            if not job_data:
                return None

            try:
                job = pickle.loads(job_data)
                return job
            except Exception as e:
                logger.error("Failed to deserialize job", job_id=job_id, error=str(e))
                return None
        finally:
            await client.aclose()
    
    async def update_job(self, job_id: str, update: JobUpdate) -> Optional[Job]:
        """Update a job in Redis."""
        if not await self._redis_available():
            return await fallback_job_store.update_job(job_id, update)

        client = self._client()
        try:
            await client.ping()

            # Get existing job
            job = await self.get_job(job_id)
            if not job:
                logger.warning("Job not found for update", job_id=job_id)
                return None

            # Remove from old status index
            await client.srem(f"{self.key_prefix}status:{job.status.value}", job_id)

            # Update fields
            if update.status:
                job.status = update.status
                if update.status == JobStatus.RUNNING and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif update.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    job.completed_at = datetime.utcnow()

            if update.result_data:
                job.result_data.update(update.result_data)

            if update.error_message:
                job.error_message = update.error_message

            # Save updated job
            job_data = pickle.dumps(job)
            await client.setex(f"{self.key_prefix}{job.id}", 86400, job_data)

            # Add to new status index
            if job.user_id:
                await client.sadd(f"{self.key_prefix}user:{job.user_id}", job.id)
            await client.sadd(f"{self.key_prefix}status:{job.status.value}", job_id)

            logger.info("Job updated in Redis", job_id=job_id, status=job.status)
            return job
        finally:
            await client.aclose()
    
    async def list_jobs(self, user_id: Optional[str] = None, status: Optional[JobStatus] = None) -> List[Job]:
        """List jobs with optional filters."""
        if not await self._redis_available():
            return await fallback_job_store.list_jobs(user_id=user_id, status=status)

        client = self._client()
        try:
            await client.ping()

            job_ids = set()

            # Get job IDs based on filters
            if user_id:
                user_jobs = await client.smembers(f"{self.key_prefix}user:{user_id}")
                job_ids.update(user_jobs or [])

            if status:
                status_jobs = await client.smembers(f"{self.key_prefix}status:{status.value}")
                if job_ids:
                    job_ids.intersection_update(status_jobs or [])
                else:
                    job_ids.update(status_jobs or [])

            # If no filters, get all jobs (limit to 1000 for performance)
            if not user_id and not status:
                pattern = f"{self.key_prefix}*"
                keys = await client.keys(pattern)
                job_ids = [key.decode().split(":")[-1] for key in keys[:1000]]

            # Fetch jobs
            jobs = []
            for job_id in job_ids:
                job = await self.get_job(job_id)
                if job:
                    jobs.append(job)

            return sorted(jobs, key=lambda j: j.created_at, reverse=True)
        finally:
            await client.aclose()
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old jobs."""
        # This is handled automatically by Redis TTL
        # But we can add additional cleanup logic if needed
        pass

# Global Redis job store instance
redis_job_store = RedisJobStore()
