import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_woocommerce_connect_and_test_flow(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("wc_owner@example.com")
    org = await create_test_org("WooCommerce Org", user)

    # 1. Create Website
    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Apex Outfitters", "url": "https://apexoutfitters.local"},
    )
    website_id = site_res.json()["id"]

    # 2. Connect WooCommerce REST API Keys
    connect_res = await client.post(
        f"/api/v1/integrations/woocommerce/connect?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "website_id": website_id,
            "api_url": "https://apexoutfitters.local",
            "consumer_key": "ck_test_1234567890abcdef",
            "consumer_secret": "cs_test_0987654321fedcba",
            "is_active": True,
        },
    )
    assert connect_res.status_code == 200
    conn_data = connect_res.json()
    assert conn_data["platform"] == "WOOCOMMERCE"
    assert conn_data["consumer_key_masked"] == "ck_t...cdef"
    assert conn_data["is_active"] is True

    # 3. Test Live Connection Endpoint
    test_res = await client.post(
        f"/api/v1/integrations/woocommerce/{website_id}/test?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert test_data["success"] is True
    assert test_data["status_code"] == 200
    assert len(test_data["sample_products"]) >= 1

    # 4. Get integration details
    get_res = await client.get(
        f"/api/v1/integrations/woocommerce/{website_id}?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["consumer_key_masked"] == "ck_t...cdef"


@pytest.mark.asyncio
async def test_woocommerce_dynamic_provider_in_rag_chat(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("wc_shopper@example.com")
    org = await create_test_org("Shopper Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Gear Store", "url": "https://gearstore.local"},
    )
    website_id = site_res.json()["id"]

    # Connect WooCommerce
    await client.post(
        f"/api/v1/integrations/woocommerce/connect?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "website_id": website_id,
            "api_url": "https://gearstore.local",
            "consumer_key": "ck_test_live_gear_store",
            "consumer_secret": "cs_test_live_secret_key",
            "is_active": True,
        },
    )

    # Initialize Visitor Session
    sess_res = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": website_id, "visitor_id": "visitor_shopper_1"},
    )
    session_token = sess_res.json()["session_token"]

    # Visitor asks for product recommendations
    msg_res = await client.post(
        "/api/v1/chat/message",
        json={
            "session_token": session_token,
            "content": "Show me wireless headphones and mechanical keyboards in stock",
        },
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["tool_call"]["tool"] == "search_product"
    assert len(msg_data["suggested_actions"]) >= 1
    assert msg_data["suggested_actions"][0]["type"] == "product_card"
    assert "gearstore.local" in msg_data["suggested_actions"][0]["value"]


@pytest.mark.asyncio
async def test_strict_tenant_isolation_woocommerce(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user_a, token_a = await create_test_user("user_a_wc@example.com")
    org_a = await create_test_org("Org A WC", user_a)

    user_b, token_b = await create_test_user("user_b_wc@example.com")
    org_b = await create_test_org("Org B WC", user_b)

    site_a = await client.post(
        f"/api/v1/websites?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Org A Store", "url": "https://store-a.local"},
    )
    site_a_id = site_a.json()["id"]

    await client.post(
        f"/api/v1/integrations/woocommerce/connect?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "website_id": site_a_id,
            "api_url": "https://store-a.local",
            "consumer_key": "ck_test_org_a",
            "consumer_secret": "cs_test_org_a",
        },
    )

    # User B tries to view Org A's WooCommerce keys -> None or 403
    res_b = await client.get(
        f"/api/v1/integrations/woocommerce/{site_a_id}?org_id={org_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 200
    assert res_b.json() is None

    # User B tries to disconnect Org A's integration -> 404
    del_b = await client.delete(
        f"/api/v1/integrations/woocommerce/{site_a_id}?org_id={org_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert del_b.status_code == 404
