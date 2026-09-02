import pytest
from httpx import AsyncClient
from app.services.whatsapp_service import WhatsAppHandoffService


def test_phone_normalization():
    assert WhatsAppHandoffService.normalize_phone_number("+1 (555) 123-4567") == "15551234567"
    assert WhatsAppHandoffService.normalize_phone_number("0044 20 7946 0912") == "442079460912"
    assert WhatsAppHandoffService.normalize_phone_number("+92-300-1234567") == "923001234567"
    assert WhatsAppHandoffService.normalize_phone_number("") == ""


def test_message_template_interpolation():
    template = "Hi {store_name}, my visitor code is {visitor_id}. Inquiry: {last_inquiry}"
    res = WhatsAppHandoffService.format_message_template(
        template=template,
        store_name="Fashion Hub",
        visitor_id="vis_991",
        session_id="sess_12345678",
        last_inquiry="Where is order #551?",
    )
    assert res == "Hi Fashion Hub, my visitor code is vis_991. Inquiry: Where is order #551?"


@pytest.mark.asyncio
async def test_whatsapp_preview_endpoint(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("wa_owner@example.com")
    org = await create_test_org("WhatsApp Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Tech Gadgets", "url": "https://techgadgets.com"},
    )
    website_id = site_res.json()["id"]

    # Preview WhatsApp link
    preview_res = await client.post(
        f"/api/v1/websites/{website_id}/whatsapp-preview?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "phone_number": "+1 (800) 555-0199",
            "custom_template": "Hello {store_name}, I need assistance regarding: {last_inquiry}",
            "visitor_id": "vis_test",
            "sample_inquiry": "Do you ship to Canada?",
        },
    )
    assert preview_res.status_code == 200
    pdata = preview_res.json()
    assert pdata["is_valid_phone"] is True
    assert pdata["clean_phone"] == "18005550199"
    assert "Tech Gadgets" in pdata["formatted_message"]
    assert "https://wa.me/18005550199?text=" in pdata["preview_url"]


@pytest.mark.asyncio
async def test_rag_chat_escalation_generates_context_rich_whatsapp_link(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("wa_chat@example.com")
    org = await create_test_org("WhatsApp Chat Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Luxury Watches", "url": "https://luxurywatches.com"},
    )
    website_id = site_res.json()["id"]

    # Enable WhatsApp in settings
    await client.put(
        f"/api/v1/websites/{website_id}/settings?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "enable_whatsapp": True,
            "whatsapp_number": "+1 555 987 6543",
            "whatsapp_custom_message": "Hi {store_name} team, please help visitor {visitor_id} regarding: {last_inquiry}",
            "whatsapp_handoff_trigger": "ON_ESCALATION",
        },
    )

    # Initialize chat session
    sess_res = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": website_id, "visitor_id": "vis_vip_customer"},
    )
    session_token = sess_res.json()["session_token"]

    # Customer asks for human agent
    msg_res = await client.post(
        "/api/v1/chat/message",
        json={"session_token": session_token, "content": "I need to talk to a human support agent on WhatsApp"},
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["tool_call"]["tool"] == "escalate_to_human"
    assert len(msg_data["suggested_actions"]) >= 1
    wa_action = msg_data["suggested_actions"][0]
    assert wa_action["type"] == "whatsapp_handoff"
    assert "wa.me/15559876543" in wa_action["value"]
    assert "Luxury%20Watches" in wa_action["value"]
