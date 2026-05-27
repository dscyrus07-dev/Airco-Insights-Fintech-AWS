"""
Authentication Middleware - Sets Audit Context Headers
Extracts user info from token and sets headers for AuditContextMiddleware
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import base64
import json

from ..services.auth_client import auth_client
from ..utils.logging import get_logger

logger = get_logger(__name__)


def _decode_bearer_payload(token: str):
    """Decode JWT token payload without verification"""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None

        payload = parts[1]
        padded = payload + "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        claims = json.loads(decoded)

        user_id = claims.get("sub") or claims.get("user_id") or claims.get("id") or claims.get("email")
        if not user_id:
            return None

        return {
            "id": user_id,
            "email": claims.get("email"),
            "name": claims.get("name") or claims.get("preferred_username") or claims.get("email"),
            "given_name": claims.get("given_name"),
            "family_name": claims.get("family_name"),
            "preferred_username": claims.get("preferred_username"),
            "roles": claims.get("realm_access", {}).get("roles", []),
        }
    except Exception as exc:
        logger.debug("Token decode failed", error=str(exc))
        return None


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract user info from token and set audit context headers.
    This runs before AuditContextMiddleware to ensure headers are available.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
        
        if token:
            # Try to verify with Auth Service
            user_info = None
            try:
                token_data = await auth_client.verify_token(token)
                if token_data and token_data.get("valid"):
                    user_info = token_data.get("user")
            except Exception as e:
                logger.debug("Auth service verification failed", error=str(e))
            
            # Fallback to local decode
            if not user_info:
                user_info = _decode_bearer_payload(token)
            
            # Set audit context headers if user is authenticated
            if user_info:
                request.headers.__dict__["_list"] = [
                    (k, v) for k, v in request.headers.items()
                    if k.lower() not in ["x-tenant-id", "x-tenant-slug", "x-user-id", 
                                        "x-user-email", "x-user-name", "x-user-role",
                                        "x-session-id"]
                ]
                
                # Add user context headers
                request.headers.__dict__["_list"].extend([
                    ("X-Tenant-ID", "default"),
                    ("X-Tenant-Slug", "default"),
                    ("X-User-ID", user_info.get("id", "")),
                    ("X-User-Email", user_info.get("email", "")),
                    ("X-User-Name", user_info.get("name", "")),
                    ("X-User-Role", "admin" if "admin" in user_info.get("roles", []) else "USER"),
                    ("X-Session-ID", token),
                ])
                
                logger.debug(f"Set audit context headers for user: {user_info.get('id')}")
        
        # Process request
        response = await call_next(request)
        
        return response
