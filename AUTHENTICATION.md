# Authentication Protection Guide

## Overview

XTS Allocator Server now includes JWT authentication. This guide shows how to protect routes with the `@require_auth()` decorator.

## Quick Start

### 1. Import Auth Decorator

```python
from auth import require_auth, ROLE_ADMIN, ROLE_ENGINEER, ROLE_READONLY, get_user_from_request
```

### 2. Protect Routes

```python
@allocation_routes.post("/allocate_slot")
@require_auth(ROLE_ENGINEER)  # Engineer or admin only
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def allocate_slot(request):
    # Access authenticated user
    user = get_user_from_request(request)
    print(f"Authenticated user: {user['email']} (role: {user['role']})")
    
    # Your route logic...
```

## Decorator Patterns

### Pattern 1: Any Authenticated User

```python
@require_auth()  # No role specified - any authenticated user
async def my_route(request):
    pass
```

### Pattern 2: Engineer or Higher

```python
@require_auth(ROLE_ENGINEER)  # Engineer or admin
async def allocate_device(request):
    pass
```

### Pattern 3: Admin Only

```python
@require_auth(ROLE_ADMIN)  # Admin only
async def force_deallocate(request):
    pass
```

### Pattern 4: Public Route (No Auth)

```python
# No decorator - publicly accessible
async def health_check(request):
    pass
```

## Route Protection Recommendations

### High Priority (Protect First)

These routes should require authentication:

```python
# Allocation routes (ROLE_ENGINEER)
@require_auth(ROLE_ENGINEER)
- POST /allocate_slot
- POST /allocate_permanent
- POST /deallocate_slot
- POST /change_device_state

# Device management (ROLE_ENGINEER for add/update/delete)
@require_auth(ROLE_ENGINEER)
- POST /add_slot
- POST /update_slot
- POST /delete_slot

# Test execution (ROLE_ENGINEER)
@require_auth(ROLE_ENGINEER)
- POST /start_test
- POST /end_test

# Admin-only routes (ROLE_ADMIN)
@require_auth(ROLE_ADMIN)
- POST /force_deallocate (if implemented)
- DELETE /allocation_history/{id}
- POST /servers/register (federation master)
```

### Medium Priority

These routes can work with readonly access:

```python
# Read-only routes (ROLE_READONLY)
@require_auth(ROLE_READONLY)
- GET /list_slots
- POST /list_slots (filtered search)
- GET /list_racks
- GET /allocation_history
- GET /usage_stats
- GET /test_executions

# Heartbeat doesn't need auth (uses test_id)
# No auth required
- POST /test_heartbeat
```

### Public Routes (No Auth)

These routes should remain public:

```python
# No authentication required
- GET /health
- GET /metrics
- GET /auth/roles
- POST /login
- POST /refresh
- GET /auth/verify
```

## Implementation Example

### Before (Unprotected)

```python
@allocation_routes.post("/allocate_slot")
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def allocate_slot(request):
    data = request.json
    user = data["user"]  # Trust client-provided user data
    # ...
```

### After (Protected)

```python
@allocation_routes.post("/allocate_slot")
@require_auth(ROLE_ENGINEER)
@rate_limit(max_requests=30, window_seconds=60, identifier_fn=user_email_identifier)
async def allocate_slot(request):
    # User is authenticated - get from token
    authenticated_user = get_user_from_request(request)
    
    # Option 1: Use authenticated user directly
    user_email = authenticated_user["email"]
    
    # Option 2: Validate client data matches authenticated user
    data = request.json
    if data.get("user", {}).get("email") != authenticated_user["email"]:
        return json({"error": "User email mismatch"}, status=403)
    
    # Continue with allocation...
```

## Testing Protected Routes

### 1. Login to Get Token

```bash
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "engineer@example.com",
    "password": "engineer123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 28800,
  "user": {
    "email": "engineer@example.com",
    "role": "engineer",
    "name": "Test Engineer"
  }
}
```

### 2. Call Protected Route

```bash
curl -X POST http://localhost:5000/allocate_slot \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -d '{
    "user": {"email": "engineer@example.com"},
    "slot": {"id": 1},
    "duration": "2h"
  }'
```

### 3. Without Token (401 Unauthorized)

```bash
curl -X POST http://localhost:5000/allocate_slot \
  -H "Content-Type: application/json" \
  -d '{
    "user": {"email": "engineer@example.com"},
    "slot": {"id": 1}
  }'
```

Response:
```json
{
  "error": "Authentication required",
  "message": "Missing authorization token"
}
```

### 4. Insufficient Role (403 Forbidden)

```bash
# Readonly user trying to allocate (requires engineer)
curl -X POST http://localhost:5000/allocate_slot \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <readonly-token>" \
  -d '{"user": {"email": "viewer@example.com"}, "slot": {"id": 1}}'
```

Response:
```json
{
  "error": "Insufficient permissions",
  "message": "Role 'engineer' or higher required"
}
```

## Demo Users

The system includes demo users for testing:

| Email | Password | Role | Capabilities |
|-------|----------|------|--------------|
| `admin@example.com` | `admin123` | `admin` | Full access |
| `engineer@example.com` | `engineer123` | `engineer` | Allocate, test, manage own devices |
| `viewer@example.com` | `viewer123` | `readonly` | View-only access |

**WARNING**: Change these credentials in production!

## Migration Strategy

### Phase 1: Opt-In Authentication (Current)

- Authentication system is available but not enforced
- Routes work with or without authentication
- Clients can continue using existing API without tokens
- New clients can authenticate for enhanced security

### Phase 2: Gradual Enforcement

1. Add `@require_auth()` to admin routes only
2. Monitor adoption and client updates
3. Add to engineer routes (allocate, test)
4. Add to readonly routes
5. Update all clients to use authentication

### Phase 3: Full Enforcement

- All routes except /login, /health, /metrics require auth
- Remove demo users, integrate with real user database
- Enable API key authentication as alternative to JWT
- Add rate limiting per user role

## Production Checklist

- [ ] Replace demo users with real user database
- [ ] Change JWT_SECRET_KEY from default
- [ ] Apply `@require_auth()` to all protected routes
- [ ] Update client applications with authentication
- [ ] Test all routes with different user roles
- [ ] Document authentication in API docs
- [ ] Set up user management interface
- [ ] Configure token expiry for your security policy
- [ ] Enable refresh token rotation
- [ ] Add audit logging for authentication events

## Troubleshooting

### "Authentication required" Error

- Check Authorization header is present
- Verify token format: `Bearer <token>`
- Ensure token hasn't expired (check expires_in)

### "Token expired" Error

- Use refresh token to get new access token
- Call POST /refresh with refresh_token

### "Insufficient permissions" Error

- Check user role matches required role
- Admin can access all routes
- Engineer can access engineer and readonly routes
- Readonly can only access readonly routes

### Token Not Working

```python
# Verify token manually
from auth import verify_token

try:
    payload = verify_token("your_token_here")
    print(payload)
except Exception as e:
    print(f"Token invalid: {e}")
```

## Support

For issues:
- Check server logs: `tail -f logs/xts_allocator.log`
- Verify config: `python -c "from config import config; config.print_config()"`
- Test token: `curl http://localhost:5000/auth/verify -H "Authorization: Bearer <token>"`
