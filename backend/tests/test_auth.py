import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_and_readiness(client: AsyncClient):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_user_registration(client: AsyncClient):
    payload = {
        "email": "alice@example.com",
        "password": "SecurePassword123!",
        "full_name": "Alice Smith",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["full_name"] == "Alice Smith"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_user_registration_duplicate_email(client: AsyncClient, create_test_user):
    await create_test_user("bob@example.com")
    payload = {
        "email": "bob@example.com",
        "password": "AnotherPassword123!",
        "full_name": "Bob Duplicate",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_user_login_success(client: AsyncClient, create_test_user):
    await create_test_user("charlie@example.com", password="SecretPassword123!")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "charlie@example.com", "password": "SecretPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "charlie@example.com"


@pytest.mark.asyncio
async def test_user_login_invalid_password(client: AsyncClient, create_test_user):
    await create_test_user("david@example.com", password="CorrectPassword123!")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "david@example.com", "password": "WrongPassword123!"},
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, create_test_user):
    user, token = await create_test_user("eva@example.com")
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "eva@example.com"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
