"""Tests for JWT authentication and authorization."""

import pytest
import jwt
from auth import (
    generate_token, verify_token, authenticate_user,
    ROLE_ADMIN, ROLE_ENGINEER, ROLE_READONLY, SECRET_KEY, ALGORITHM
)


class TestTokenGeneration:
    """Test JWT token generation."""
    
    def test_generate_access_token(self):
        """Test generating access token."""
        token = generate_token("user@example.com", ROLE_ENGINEER, "access")
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["email"] == "user@example.com"
        assert payload["role"] == ROLE_ENGINEER
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
    
    def test_generate_refresh_token(self):
        """Test generating refresh token."""
        token = generate_token("user@example.com", ROLE_ADMIN, "refresh")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert payload["email"] == "user@example.com"
        assert payload["role"] == ROLE_ADMIN
        assert payload["type"] == "refresh"
    
    def test_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            generate_token("user@example.com", "superuser", "access")


class TestTokenVerification:
    """Test JWT token verification."""
    
    def test_verify_valid_token(self):
        """Test verifying valid token."""
        token = generate_token("test@example.com", ROLE_ENGINEER)
        payload = verify_token(token)
        
        assert payload["email"] == "test@example.com"
        assert payload["role"] == ROLE_ENGINEER
    
    def test_verify_invalid_token(self):
        """Test verifying invalid token."""
        with pytest.raises(jwt.InvalidTokenError):
            verify_token("invalid.token.here")
    
    def test_verify_expired_token(self):
        """Test verifying expired token."""
        # Create token that expires immediately
        import time
        from datetime import datetime, timedelta, timezone

        expire = datetime.now(timezone.utc) - timedelta(seconds=1)  # Already expired
        payload = {
            "email": "user@example.com",
            "role": ROLE_ENGINEER,
            "exp": expire
        }
        expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_token(expired_token)


class TestUserAuthentication:
    """Test user authentication."""
    
    def test_authenticate_valid_user(self):
        """Test authenticating valid user."""
        user = authenticate_user("engineer@example.com", "engineer123")
        assert user is not None
        assert user["email"] == "engineer@example.com"
        assert user["role"] == ROLE_ENGINEER
        assert user["name"] == "Test Engineer"
    
    def test_authenticate_admin(self):
        """Test authenticating admin user."""
        user = authenticate_user("admin@example.com", "admin123")
        assert user is not None
        assert user["role"] == ROLE_ADMIN
    
    def test_authenticate_invalid_email(self):
        """Test authenticating with invalid email."""
        user = authenticate_user("nonexistent@example.com", "password")
        assert user is None
    
    def test_authenticate_invalid_password(self):
        """Test authenticating with invalid password."""
        user = authenticate_user("engineer@example.com", "wrongpassword")
        assert user is None


class TestAuthRoutes:
    """Test authentication API endpoints."""
    
    def test_login_success(self, test_client):
        """Test successful login."""
        request, response = test_client.post(
            "/login",
            json={
                "email": "engineer@example.com",
                "password": "engineer123"
            }
        )
        
        assert response.status == 200
        data = response.json
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "expires_in" in data
        assert data["user"]["email"] == "engineer@example.com"
        assert data["user"]["role"] == ROLE_ENGINEER
    
    def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials."""
        request, response = test_client.post(
            "/login",
            json={
                "email": "engineer@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status == 401
        data = response.json
        assert "error" in data
        assert data["error"] == "Authentication failed"
    
    def test_login_missing_email(self, test_client):
        """Test login with missing email."""
        request, response = test_client.post(
            "/login",
            json={
                "password": "engineer123"
            }
        )
        
        assert response.status == 400
        data = response.json
        assert "error" in data
    
    def test_login_invalid_email_format(self, test_client):
        """Test login with invalid email format."""
        request, response = test_client.post(
            "/login",
            json={
                "email": "not-an-email",
                "password": "password123"
            }
        )
        
        assert response.status == 400
    
    def test_refresh_token_success(self, test_client):
        """Test successful token refresh."""
        # First login to get refresh token
        _, login_response = test_client.post(
            "/login",
            json={
                "email": "engineer@example.com",
                "password": "engineer123"
            }
        )
        refresh_token = login_response.json["refresh_token"]
        
        # Refresh token
        request, response = test_client.post(
            "/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status == 200
        data = response.json
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
    
    def test_refresh_with_access_token_fails(self, test_client):
        """Test that refresh fails with access token."""
        # Get access token
        _, login_response = test_client.post(
            "/login",
            json={
                "email": "engineer@example.com",
                "password": "engineer123"
            }
        )
        access_token = login_response.json["access_token"]
        
        # Try to refresh with access token
        request, response = test_client.post(
            "/refresh",
            json={"refresh_token": access_token}
        )
        
        assert response.status == 400
        assert "Invalid token type" in response.json["error"]
    
    def test_verify_token_success(self, test_client):
        """Test token verification endpoint."""
        # Login and get token
        _, login_response = test_client.post(
            "/login",
            json={
                "email": "admin@example.com",
                "password": "admin123"
            }
        )
        access_token = login_response.json["access_token"]
        
        # Verify token
        request, response = test_client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert response.status == 200
        data = response.json
        assert data["valid"] is True
        assert data["user"]["email"] == "admin@example.com"
        assert data["user"]["role"] == ROLE_ADMIN
    
    def test_verify_token_no_auth_header(self, test_client):
        """Test verification without auth header."""
        request, response = test_client.get("/auth/verify")
        
        assert response.status == 401
        data = response.json
        assert data["valid"] is False
    
    def test_get_roles(self, test_client):
        """Test getting available roles."""
        request, response = test_client.get("/auth/roles")
        
        assert response.status == 200
        data = response.json
        assert "roles" in data
        assert len(data["roles"]) == 3
        
        roles = {role["name"]: role for role in data["roles"]}
        assert ROLE_ADMIN in roles
        assert ROLE_ENGINEER in roles
        assert ROLE_READONLY in roles
        assert roles[ROLE_ADMIN]["level"] == 2
        assert roles[ROLE_ENGINEER]["level"] == 1
        assert roles[ROLE_READONLY]["level"] == 0
