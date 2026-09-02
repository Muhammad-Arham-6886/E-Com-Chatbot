# Authentication & Session Management

## Endpoints

### 1. User Registration
`POST /api/v1/auth/register`
Request:
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!",
  "full_name": "Jane Doe"
}
```
Response (`201 Created`):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-08-19T20:00:00Z"
}
```

### 2. User Login
`POST /api/v1/auth/login`
Request:
```json
{
  "email": "user@example.com",
  "password": "StrongPassword123!"
}
```
Response (`200 OK`):
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "Jane Doe"
  }
}
```

### 3. Current User Profile
`GET /api/v1/auth/me`
Header: `Authorization: Bearer <token>`
Response (`200 OK`):
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "is_active": true
}
```

### 4. Logout
`POST /api/v1/auth/logout`
Header: `Authorization: Bearer <token>`
Response (`200 OK`):
```json
{
  "message": "Successfully logged out"
}
```
