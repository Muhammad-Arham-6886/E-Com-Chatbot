import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_static_widget_file_serving(client: AsyncClient):
    res = await client.get("/static/widget.js")
    assert res.status_code == 200
    assert "application/javascript" in res.headers.get("content-type", "") or "text/javascript" in res.headers.get("content-type", "")
    assert "AI Customer & Commerce Assistant" in res.text
    assert "attachShadow" in res.text


@pytest.mark.asyncio
async def test_widget_public_config_and_session_lifecycle(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("widget_owner@example.com")
    org = await create_test_org("Widget Corp", user)

    # 1. Create Website
    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Widget Store", "url": "https://widgetstore.io"},
    )
    assert site_res.status_code == 201
    site_data = site_res.json()
    public_site_id = site_data["public_site_id"]
    website_id = site_data["id"]

    # 2. Update widget appearance settings
    await client.put(
        f"/api/v1/websites/{website_id}/settings?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "chatbot_name": "Store Bot",
            "primary_color": "#10b981",
            "greeting_message": "Welcome to our store! Ask us anything.",
            "widget_position": "bottom-right",
            "enable_whatsapp": True,
            "whatsapp_number": "+18005550199",
        },
    )

    # 3. Fetch public config without auth headers
    config_res = await client.get(f"/api/v1/websites/public/{public_site_id}/config")
    assert config_res.status_code == 200
    config_data = config_res.json()
    assert config_data["website_id"] == website_id
    assert config_data["chatbot_name"] == "Store Bot"
    assert config_data["primary_color"] == "#10b981"
    assert config_data["enable_whatsapp"] is True

    # 4. Initialize session from widget
    sess_res = await client.post(
        "/api/v1/chat/sessions",
        json={
            "website_id": website_id,
            "visitor_id": "widget_visitor_42",
            "channel": "WEB_WIDGET",
        },
    )
    assert sess_res.status_code == 201
    session_token = sess_res.json()["session_token"]

    # 5. Send message from widget
    msg_res = await client.post(
        "/api/v1/chat/message",
        json={
            "session_token": session_token,
            "content": "Can I talk to human support on WhatsApp?",
        },
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["sender"] == "BOT"
    assert len(msg_data["suggested_actions"]) >= 1
    assert msg_data["suggested_actions"][0]["type"] == "whatsapp_handoff"
    assert "18005550199" in msg_data["suggested_actions"][0]["value"]
