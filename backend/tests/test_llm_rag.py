import pytest
from httpx import AsyncClient
from app.models.crawling import KnowledgeDocument
from app.models.enums import DocumentStatusEnum
from app.services.ai.tool_selector import ToolSelectionEngine, ToolType
from app.services.ai.commerce_provider import MockCommerceProvider


def test_tool_selection_classification():
    # 1. Human Escalation
    res1 = ToolSelectionEngine.classify("I want to speak with a human agent on whatsapp")
    assert res1.tool == ToolType.ESCALATE_HUMAN

    # 2. Add to cart
    res2 = ToolSelectionEngine.classify("Add this item to my cart please")
    assert res2.tool == ToolType.ADD_TO_CART

    # 3. Product Search
    res3 = ToolSelectionEngine.classify("Do you sell mechanical keyboards or headphones?")
    assert res3.tool == ToolType.SEARCH_PRODUCT

    # 4. Knowledge / General Inquiry
    res4 = ToolSelectionEngine.classify("What is your refund and return policy?")
    assert res4.tool == ToolType.KNOWLEDGE_INQUIRY


@pytest.mark.asyncio
async def test_commerce_mock_provider():
    provider = MockCommerceProvider()
    products = await provider.search_products("headphones")
    assert len(products) >= 1
    assert "Headphones" in products[0].name
    assert products[0].price > 0

    cart_url = await provider.get_add_to_cart_url("prod_001", quantity=2)
    assert "add-to-cart=prod_001" in cart_url
    assert "quantity=2" in cart_url


@pytest.mark.asyncio
async def test_chat_session_creation_and_messaging_flow(client: AsyncClient, create_test_user, create_test_org, db_session):
    user, token = await create_test_user("chat_user@example.com")
    org = await create_test_org("Chat Org", user)

    # 1. Create Website
    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Support Store", "url": "https://supportstore.com"},
    )
    website_id = site_res.json()["id"]

    # 2. Add Website Knowledge Document & Embeddings
    doc = KnowledgeDocument(
        website_id=website_id,
        organization_id=org.id,
        url="https://supportstore.com/shipping-policy",
        title="Shipping & Delivery Policy",
        raw_content="We provide free 2-day express shipping on all orders exceeding $75 in the continental US.",
        content_hash="hash_shipping_75",
        token_count=20,
        status=DocumentStatusEnum.RAW,
    )
    db_session.add(doc)
    await db_session.commit()

    # Process embeddings
    await client.post(
        f"/api/v1/knowledge/websites/{website_id}/process-embeddings?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"re_embed_all": True},
    )

    # 3. Create Chat Session
    sess_res = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": website_id, "visitor_id": "test_visitor_99"},
    )
    assert sess_res.status_code == 201
    session_data = sess_res.json()
    session_id = session_data["id"]
    session_token = session_data["session_token"]

    # 4. Send Knowledge Query: "How much is shipping?"
    msg_res = await client.post(
        "/api/v1/chat/message",
        json={"session_token": session_token, "content": "How much is shipping?"},
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["sender"] == "BOT"
    assert len(msg_data["content"]) > 0
    assert len(msg_data["sources"]) >= 1
    assert "Shipping & Delivery Policy" in msg_data["sources"][0]["title"]

    # 5. Send Product Search Query: "Show me headphones"
    prod_msg_res = await client.post(
        "/api/v1/chat/message",
        json={"session_token": session_token, "content": "Do you sell any headphones in stock?"},
    )
    assert prod_msg_res.status_code == 200
    prod_data = prod_msg_res.json()
    assert prod_data["tool_call"]["tool"] == "search_product"
    assert len(prod_data["suggested_actions"]) >= 1
    assert prod_data["suggested_actions"][0]["type"] == "product_card"

    # 6. Retrieve Session Messages History
    history_res = await client.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assert history_res.status_code == 200
    messages = history_res.json()
    # 2 user messages + 2 bot replies = 4 messages
    assert len(messages) == 4
    assert messages[0]["sender"] == "USER"
    assert messages[1]["sender"] == "BOT"


@pytest.mark.asyncio
async def test_rag_test_debug_endpoint(client: AsyncClient, create_test_user, create_test_org, db_session):
    user, token = await create_test_user("debug_user@example.com")
    org = await create_test_org("Debug Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Debug Site", "url": "https://debugsite.com"},
    )
    site_id = site_res.json()["id"]

    # Enable WhatsApp in settings
    await client.put(
        f"/api/v1/websites/{site_id}/settings?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "enable_whatsapp": True,
            "whatsapp_number": "+15559876543",
        },
    )

    test_res = await client.post(
        f"/api/v1/chat/test-rag?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"website_id": site_id, "message": "I want to speak with a human support agent on whatsapp"},
    )
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["tool_call"]["tool"] == "escalate_to_human"
    assert len(test_data["suggested_actions"]) >= 1
    assert test_data["suggested_actions"][0]["type"] == "whatsapp_handoff"
    assert "wa.me/15559876543" in test_data["suggested_actions"][0]["value"]
