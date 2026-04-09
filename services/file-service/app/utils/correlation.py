"""
Correlation ID utilities for File Service.
"""

import uuid

def generate_job_id() -> str:
    """Generate a unique job ID."""
    return str(uuid.uuid4())

def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())
