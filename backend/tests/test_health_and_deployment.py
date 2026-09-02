import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness_probe(client: AsyncClient):
    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-customer-commerce-saas"


@pytest.mark.asyncio
async def test_readiness_probe_with_components(client: AsyncClient):
    res = await client.get("/api/v1/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    components = data["components"]
    assert components["database"] == "connected"
    assert "ollama_service" in components
    assert "pgvector_extension" in components
