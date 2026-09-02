import pytest
from httpx import AsyncClient
from app.models.enums import RoleEnum


@pytest.mark.asyncio
async def test_list_conversations_and_transcript_flow(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("agent_lead@example.com")
    org = await create_test_org("Conversations Org", user)

    # 1. Create Website
    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Retail Store", "url": "https://retailstore.com"},
    )
    website_id = site_res.json()["id"]

    # 2. Create Two Visitor Sessions
    sess1_res = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": website_id, "visitor_id": "visitor_alice", "channel": "WEB_WIDGET"},
    )
    sess1_token = sess1_res.json()["session_token"]
    sess1_id = sess1_res.json()["id"]

    sess2_res = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": website_id, "visitor_id": "visitor_bob", "channel": "WEB_WIDGET"},
    )
    sess2_token = sess2_res.json()["session_token"]

    # 3. Send message in session 1
    await client.post(
        "/api/v1/chat/message",
        json={"session_token": sess1_token, "content": "What are your business hours?"},
    )

    # 4. List conversations
    list_res = await client.get(
        f"/api/v1/conversations?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 2
    assert len(list_data["items"]) == 2
    assert any(c["visitor_id"] == "visitor_alice" for c in list_data["items"])

    # 5. Get full transcript of session 1
    detail_res = await client.get(
        f"/api/v1/conversations/{sess1_id}?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["session"]["id"] == sess1_id
    assert detail_data["website_name"] == "Retail Store"
    assert len(detail_data["messages"]) >= 2
    assert detail_data["messages"][0]["sender"] == "USER"
    assert detail_data["messages"][1]["sender"] == "BOT"


@pytest.mark.asyncio
async def test_human_agent_takeover_and_reply_flow(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("support_agent@example.com")
    org = await create_test_org("Agent Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Support Hub", "url": "https://supporthub.com"},
    )
    website_id = site_res.json()["id"]

    # Visitor opens session & asks question
    sess_res = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": website_id, "visitor_id": "vis_charlie"},
    )
    sess_id = sess_res.json()["id"]
    sess_token = sess_res.json()["session_token"]

    await client.post(
        "/api/v1/chat/message",
        json={"session_token": sess_token, "content": "I need help with my custom invoice"},
    )

    # Human agent sends reply via Agent Inbox
    reply_res = await client.post(
        f"/api/v1/conversations/{sess_id}/agent-reply?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Hi Charlie, I am taking over this ticket. Let me review your invoice details."},
    )
    assert reply_res.status_code == 201
    reply_data = reply_res.json()
    assert reply_data["sender"] == "AGENT"
    assert "taking over" in reply_data["content"]

    # Verify session status is now HUMAN_TAKEOVER
    detail_res = await client.get(
        f"/api/v1/conversations/{sess_id}?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.json()["session"]["status"] == "HUMAN_TAKEOVER"
    assert detail_res.json()["session"]["assigned_user_id"] == user.id

    # If visitor sends message during human takeover, AI bot does not generate hallucinated reply
    vis_msg2 = await client.post(
        "/api/v1/chat/message",
        json={"session_token": sess_token, "content": "Thank you, here is invoice #4092."},
    )
    assert vis_msg2.status_code == 200
    assert vis_msg2.json()["sender"] == "SYSTEM"

    # Agent closes the conversation
    close_res = await client.put(
        f"/api/v1/conversations/{sess_id}/status?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "CLOSED"},
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"


@pytest.mark.asyncio
async def test_strict_tenant_isolation_conversations(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user_a, token_a = await create_test_user("user_a_inbox@example.com")
    org_a = await create_test_org("Org A", user_a)

    user_b, token_b = await create_test_user("user_b_inbox@example.com")
    org_b = await create_test_org("Org B", user_b)

    site_a = await client.post(
        f"/api/v1/websites?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Org A Site", "url": "https://site-a.com"},
    )
    site_a_id = site_a.json()["id"]

    sess_a = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": site_a_id, "visitor_id": "secret_visitor_a"},
    )
    sess_a_id = sess_a.json()["id"]

    # User B tries to view Org A's conversation list -> 403 Forbidden
    list_b = await client.get(
        f"/api/v1/conversations?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_b.status_code == 403

    # User B tries to get Org A's conversation detail with their own org_id -> 404
    detail_b = await client.get(
        f"/api/v1/conversations/{sess_a_id}?org_id={org_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert detail_b.status_code == 404
