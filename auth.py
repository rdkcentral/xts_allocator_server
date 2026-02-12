"""
JWT authentication middleware for XTS Allocator Server.
Provides token generation, validation, and role-based access control.
"""

import jwt
import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from sanic.response import json as sanic_json
from logging_config import get_logger
from typing import Optional

logger = get_logger()

# Lazy import audit_log to avoid circular imports
_audit_log = None
def get_audit_log():
    global _audit_log
    if _audit_log is None:
        import audit_log as _al
        _audit_log = _al
    return _audit_log

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "xts-allocator-dev-secret-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours
REFRESH_TOKEN_EXPIRE_DAYS = 30

# User roles
ROLE_ADMIN = "admin"
ROLE_ENGINEER = "engineer"
ROLE_READONLY = "readonly"

VALID_ROLES = [ROLE_ADMIN, ROLE_ENGINEER, ROLE_READONLY]


def generate_token(email: str, role: str = ROLE_ENGINEER, token_type: str = "access") -> str:
    """
    Generate JWT token for user.
    
    Args:
        email: User email
        role: User role (admin/engineer/readonly)
        token_type: Token type (access/refresh)
        
    Returns:
        Encoded JWT token
    """
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role: {role}. Must be one of {VALID_ROLES}")
    
    expires_delta = (
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) 
        if token_type == "access" 
        else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        "email": email,
        "role": role,
        "type": token_type,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.ExpiredSignatureError: Token expired
        jwt.InvalidTokenError: Invalid token
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise


def extract_token(request) -> str:
    """
    Extract JWT token from request header.
    
    Args:
        request: Sanic request object
        
    Returns:
        Token string or None
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    
    # Support "Bearer <token>" format
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    
    # Support direct token
    return auth_header


def require_auth(required_role: str = None):
    """
    Decorator to protect routes with JWT authentication.
    
    Args:
        required_role: Minimum required role (admin > engineer > readonly)
        
    Usage:
        @require_auth()  # Any authenticated user
        @require_auth(ROLE_ENGINEER)  # Engineer or admin only
        @require_auth(ROLE_ADMIN)  # Admin only
    """
    def decorator(f):
        @wraps(f)
        async def decorated_function(request, *args, **kwargs):
            # Extract token
            token = extract_token(request)
            if not token:
                return sanic_json({
                    "error": "Authentication required",
                    "message": "Missing authorization token"
                }, status=401)
            
            # Verify token
            try:
                payload = verify_token(token)
            except jwt.ExpiredSignatureError:
                return sanic_json({
                    "error": "Token expired",
                    "message": "Please login again"
                }, status=401)
            except jwt.InvalidTokenError:
                return sanic_json({
                    "error": "Invalid token",
                    "message": "Authentication failed"
                }, status=401)
            
            # Check token type
            if payload.get("type") != "access":
                return sanic_json({
                    "error": "Invalid token type",
                    "message": "Access token required"
                }, status=401)
            
            # Check role hierarchy
            user_role = payload.get("role", ROLE_READONLY)
            if required_role:
                role_hierarchy = {
                    ROLE_READONLY: 0,
                    ROLE_ENGINEER: 1,
                    ROLE_ADMIN: 2
                }
                
                user_level = role_hierarchy.get(user_role, 0)
                required_level = role_hierarchy.get(required_role, 0)
                
                if user_level < required_level:
                    # Log unauthorized access attempt
                    audit = get_audit_log()
                    source_ip = request.headers.get("X-Forwarded-For", request.ip).split(",")[0].strip()
                    audit.log_unauthorized_access(
                        endpoint=request.path,
                        user_email=payload.get("email"),
                        required_role=required_role,
                        user_role=user_role,
                        source_ip=source_ip
                    )
                    
                    return sanic_json({
                        "error": "Insufficient permissions",
                        "message": f"Role '{required_role}' or higher required"
                    }, status=403)
            
            # Attach user info to request
            request.ctx.user = {
                "email": payload.get("email"),
                "role": user_role
            }
            
            # Call original function
            response = await f(request, *args, **kwargs)
            return response
        
        return decorated_function
    return decorator


def get_user_from_request(request) -> dict:
    """
    Get authenticated user info from request context.
    
    Args:
        request: Sanic request object
        
    Returns:
        User dict with email and role, or None if not authenticated
    """
    return getattr(request.ctx, "user", None)


def is_admin(request) -> bool:
    """Check if authenticated user is admin."""
    user = get_user_from_request(request)
    return user and user.get("role") == ROLE_ADMIN


def is_engineer_or_admin(request) -> bool:
    """Check if authenticated user is engineer or admin."""
    user = get_user_from_request(request)
    if not user:
        return False
    role = user.get("role")
    return role in [ROLE_ENGINEER, ROLE_ADMIN]


# Demo user database (replace with real database)
DEMO_USERS = {
    "admin@example.com": {
        "password": "admin123",  # In production: use bcrypt hashed passwords
        "role": ROLE_ADMIN,
        "name": "Admin User"
    },
    "engineer@example.com": {
        "password": "engineer123",
        "role": ROLE_ENGINEER,
        "name": "Test Engineer"
    },
    "viewer@example.com": {
        "password": "viewer123",
        "role": ROLE_READONLY,
        "name": "Read-Only Viewer"
    }
}


def authenticate_user(email: str, password: str) -> dict:
    """
    Authenticate user with email/password.
    
    Args:
        email: User email
        password: User password (plain text - compare with hashed in production)
        
    Returns:
        User dict if authenticated, None otherwise
    """
    user = DEMO_USERS.get(email)
    if not user:
        return None
    
    # In production: use bcrypt.checkpw(password.encode(), user['password_hash'])
    if user["password"] == password:
        return {
            "email": email,
            "role": user["role"],
            "name": user["name"]
        }
    
    return None
