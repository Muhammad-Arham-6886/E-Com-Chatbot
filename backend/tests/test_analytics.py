import json
import pytest
from httpx import AsyncClient
from app.models.chat import ChatSession, ChatMessage


@pytest.mark.asyncio
async def test_analytics_kpi_overview_aggregation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("analytics_usr@example.com")
    org = await create_test_org("Analytics Corp", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Analytics Store", "url": "https://analytics-store.com"},
    )
    site_id = site_res.json()["id"]

    # Create 2 chat sessions
    s1_res = await client.post("/api/v1/chat/sessions", json={"website_id": site_id})
    s1_token = s1_res.json()["session_token"]
    s1_id = s1_res.json()["id"]

    s2_res = await client.post("/api/v1/chat/sessions", json={"website_id": site_id})
    s2_token = s2_res.json()["session_token"]

    # Send messages in session 1 (product inquiry + add to cart)
    await client.post(
        "/api/v1/chat/message",
        json={"session_token": s1_token, "content": "I want to buy running shoes size 10"},
    )

    # Escalated session 2
    await client.post(
        "/api/v1/chat/message",
        json={"session_token": s2_token, "content": "Can I speak to a human support agent please?"},
    )

    # Fetch Analytics Overview
    kpi_res = await client.get(
        f"/api/v1/analytics/overview?org_id={org.id}&period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert kpi_res.status_code == 200
    kpis = kpi_res.json()
    assert kpis["total_conversations"] == 2
    assert kpis["total_messages"] >= 4
    assert kpis["user_messages"] >= 2
    assert kpis["bot_messages"] >= 2
    assert "bot_containment_rate" in kpis
    assert "human_escalation_rate" in kpis


@pytest.mark.asyncio
async def test_analytics_timeseries_intents_and_conversions(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("charts_user@example.com")
    org = await create_test_org("Charts Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Charts Store", "url": "https://charts-store.com"},
    )
    site_id = site_res.json()["id"]

    # 1. Timeseries endpoint
    ts_res = await client.get(
        f"/api/v1/analytics/timeseries?org_id={org.id}&period=7d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ts_res.status_code == 200
    points = ts_res.json()["points"]
    assert len(points) == 7
    assert "conversations" in points[0]
    assert "date" in points[0]

    # 2. Intents endpoint
    intents_res = await client.get(
        f"/api/v1/analytics/intents?org_id={org.id}&period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert intents_res.status_code == 200
    intents = intents_res.json()["intents"]
    assert len(intents) >= 4
    intent_names = [i["intent"] for i in intents]
    assert "Product Discovery & Search" in intent_names

    # 3. Conversions endpoint
    conv_res = await client.get(
        f"/api/v1/analytics/conversions?org_id={org.id}&period=30d",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conv_res.status_code == 200
    stages = conv_res.json()["stages"]
    assert len(stages) == 4
    assert stages[0]["stage"] == "Chat Sessions Started"


@pytest.mark.asyncio
async def test_analytics_strict_tenant_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user_a, token_a = await create_test_user("user_a_stat@example.com")
    org_a = await create_test_org("Stat Org A", user_a)

    user_b, token_b = await create_test_user("user_b_stat@example.com")
    org_b = await create_test_org("Stat Org B", user_b)

    # User B tries to query Org A's analytics -> 403
    hacked_res = await client.get(
        f"/api/v1/analytics/overview?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert hacked_res.status_code == 403
