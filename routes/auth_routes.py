"""Authentication routes for login, token refresh, and user management."""

from sanic import Blueprint
from sanic.response import json
from auth import generate_token, verify_token, authenticate_user, ROLE_ADMIN, ROLE_ENGINEER, ROLE_READONLY
from input_validation import validate_email, validate_string, ValidationError
from logging_config import get_logger
from audit_log import log_auth_attempt, log_audit_event, EVENT_AUTH_TOKEN_REFRESH, CATEGORY_AUTHENTICATION, SEVERITY_INFO
import jwt

auth_routes = Blueprint("auth_routes")
logger = get_logger()


def get_client_ip(request):
    """Extract client IP from request, considering proxies."""
    return request.headers.get("X-Forwarded-For", request.ip).split(",")[0].strip()


@auth_routes.post("/login")
async def login(request):
    """
    Authenticate user and return JWT tokens.
    
    Request body:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Response:
        {
            "access_token": "...",
            "refresh_token": "...",
            "token_type": "Bearer",
            "expires_in": 28800,
            "user": {
                "email": "user@example.com",
                "role": "engineer",
                "name": "Test Engineer"
            }
        }
    """
    try:
        data = request.json
        
        # Validate inputs
        try:
            email = validate_email(data.get("email"))
            password = validate_string(data.get("password"), "password", min_length=6, max_length=100)
        except ValidationError as e:
            return json({"error": str(e)}, status=400)
        
        # Authenticate user
        user = authenticate_user(email, password)
        source_ip = get_client_ip(request)
        
        if not user:
            logger.warning(f"Failed login attempt for: {email}")
            # Log failed auth attempt
            log_auth_attempt(email, success=False, source_ip=source_ip, 
                           error_message="Invalid credentials")
            return json({
                "error": "Authentication failed",
                "message": "Invalid email or password"
            }, status=401)
        
        # Generate tokens
        access_token = generate_token(user["email"], user["role"], token_type="access")
        refresh_token = generate_token(user["email"], user["role"], token_type="refresh")
        
        logger.info(f"User logged in: {user['email']} (role: {user['role']})")
        
        # Log successful auth attempt
        log_auth_attempt(email, success=True, source_ip=source_ip)
        
        return json({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 28800,  # 8 hours in seconds
            "user": {
                "email": user["email"],
                "role": user["role"],
                "name": user["name"]
            }
        }, status=200)
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return json({"error": "Internal server error"}, status=500)


@auth_routes.post("/refresh")
async def refresh_token_endpoint(request):
    """
    Refresh access token using refresh token.
    
    Request body:
        {
            "refresh_token": "..."
        }
    
    Response:
        {
            "access_token": "...",
            "token_type": "Bearer",
            "expires_in": 28800
        }
    """
    try:
        data = request.json
        refresh_token = data.get("refresh_token")
        
        if not refresh_token:
            return json({"error": "refresh_token is required"}, status=400)
        
        # Verify refresh token
        try:
            payload = verify_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return json({
                "error": "Refresh token expired",
                "message": "Please login again"
            }, status=401)
        except jwt.InvalidTokenError:
            return json({
                "error": "Invalid refresh token"
            }, status=401)
        
        # Check token type
        if payload.get("type") != "refresh":
            return json({
                "error": "Invalid token type",
                "message": "Refresh token required"
            }, status=400)
        
        # Generate new access token
        email = payload.get("email")
        role = payload.get("role", ROLE_ENGINEER)
        access_token = generate_token(email, role, token_type="access")
        
        logger.info(f"Token refreshed for: {email}")
        
        # Log token refresh
        source_ip = get_client_ip(request)
        log_audit_event(
            event_type=EVENT_AUTH_TOKEN_REFRESH,
            event_category=CATEGORY_AUTHENTICATION,
            action=f"Access token refreshed for {email}",
            user_email=email,
            user_role=role,
            endpoint="/auth/refresh",
            http_method="POST",
            source_ip=source_ip,
            success=True,
            status_code=200,
            severity=SEVERITY_INFO
        )
        
        return json({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 28800
        }, status=200)
    
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        return json({"error": "Internal server error"}, status=500)


@auth_routes.get("/auth/verify")
async def verify_token_endpoint(request):
    """
    Verify if current token is valid.
    Useful for checking auth status on frontend.
    
    Headers:
        Authorization: Bearer <token>
    
    Response:
        {
            "valid": true,
            "user": {
                "email": "user@example.com",
                "role": "engineer"
            },
            "expires_at": "2026-02-07T20:30:00Z"
        }
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return json({"valid": False, "error": "No token provided"}, status=401)
        
        # Extract token
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            token = auth_header
        
        # Verify token
        try:
            payload = verify_token(token)
        except jwt.ExpiredSignatureError:
            return json({"valid": False, "error": "Token expired"}, status=401)
        except jwt.InvalidTokenError:
            return json({"valid": False, "error": "Invalid token"}, status=401)
        
        # Return token info
        return json({
            "valid": True,
            "user": {
                "email": payload.get("email"),
                "role": payload.get("role")
            },
            "expires_at": payload.get("exp"),
            "token_type": payload.get("type")
        }, status=200)
    
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}", exc_info=True)
        return json({"error": "Internal server error"}, status=500)


@auth_routes.get("/auth/roles")
async def get_roles(request):
    """
    Get available user roles.
    Public endpoint - no authentication required.
    
    Response:
        {
            "roles": [
                {"name": "admin", "level": 2, "description": "Full system access"},
                {"name": "engineer", "level": 1, "description": "Allocate and manage own devices"},
                {"name": "readonly", "level": 0, "description": "View-only access"}
            ]
        }
    """
    return json({
        "roles": [
            {
                "name": ROLE_ADMIN,
                "level": 2,
                "description": "Full system access - manage all devices, users, and system settings"
            },
            {
                "name": ROLE_ENGINEER,
                "level": 1,
                "description": "Allocate and manage devices, run tests, standard operations"
            },
            {
                "name": ROLE_READONLY,
                "level": 0,
                "description": "View-only access - cannot allocate or modify devices"
            }
        ]
    }, status=200)
