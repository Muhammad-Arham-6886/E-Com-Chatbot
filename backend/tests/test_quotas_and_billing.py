import pytest
from httpx import AsyncClient
from app.services.quota_service import QuotaService


@pytest.mark.asyncio
async def test_free_tier_website_limit_enforced(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("quota_free@example.com")
    org = await create_test_org("Quota Free Org", user)

    # 1. First website creation should succeed (Free tier limit = 1)
    res1 = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "First Site", "url": "https://first-site.com"},
    )
    assert res1.status_code == 201

    # 2. Second website creation on Free tier should fail with 402 Payment Required
    res2 = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Second Site", "url": "https://second-site.com"},
    )
    assert res2.status_code == 402
    assert "Website limit" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_upgrade_tier_relaxes_quota(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("upgrade_user@example.com")
    org = await create_test_org("Upgrade Org", user)

    # Create 1st site
    await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Site 1", "url": "https://site1.com"},
    )

    # Attempt 2nd site -> 402
    res_blocked = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Site 2", "url": "https://site2.com"},
    )
    assert res_blocked.status_code == 402

    # Upgrade to STARTER (Allows 3 websites)
    upgrade_res = await client.post(
        f"/api/v1/billing/change-tier?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"tier": "STARTER"},
    )
    assert upgrade_res.status_code == 200
    assert upgrade_res.json()["tier"] == "STARTER"

    # Now 2nd site succeeds
    res_site2 = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Site 2", "url": "https://site2.com"},
    )
    assert res_site2.status_code == 201

    # 3rd site succeeds
    res_site3 = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Site 3", "url": "https://site3.com"},
    )
    assert res_site3.status_code == 201

    # 4th site fails (Starter limit = 3)
    res_site4 = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Site 4", "url": "https://site4.com"},
    )
    assert res_site4.status_code == 402


@pytest.mark.asyncio
async def test_chat_message_quota_enforcement_and_usage_tracking(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("chat_quota_user@example.com")
    org = await create_test_org("Chat Quota Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Chat Quota Store", "url": "https://chatquota.com"},
    )
    site_data = site_res.json()
    website_id = site_data["id"]

    # Start public visitor chat session
    sess_res = await client.post(
        "/api/v1/chat/sessions",
        json={"website_id": website_id},
    )
    assert sess_res.status_code == 201
    session_token = sess_res.json()["session_token"]

    # Check initial usage
    usage_res = await client.get(
        f"/api/v1/billing/usage?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage_res.json()["chat_messages"]["used"] == 0

    # Send a visitor message
    msg_res = await client.post(
        "/api/v1/chat/message",
        json={"session_token": session_token, "content": "Hello bot!"},
    )
    assert msg_res.status_code == 200

    # Verify usage was incremented
    usage_res2 = await client.get(
        f"/api/v1/billing/usage?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage_res2.json()["chat_messages"]["used"] == 1


@pytest.mark.asyncio
async def test_billing_endpoints_and_tiers_list(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user_a, token_a = await create_test_user("bill_user_a@example.com")
    org_a = await create_test_org("Org Billing A", user_a)

    user_b, token_b = await create_test_user("bill_user_b@example.com")
    org_b = await create_test_org("Org Billing B", user_b)

    # 1. Get tiers list
    tiers_res = await client.get("/api/v1/billing/tiers")
    assert tiers_res.status_code == 200
    tiers = tiers_res.json()
    assert len(tiers) == 4
    tier_names = [t["tier"] for t in tiers]
    assert "FREE" in tier_names
    assert "STARTER" in tier_names
    assert "GROWTH" in tier_names
    assert "ENTERPRISE" in tier_names

    # 2. Strict tenant isolation: User B cannot change Org A's tier
    hacked_res = await client.post(
        f"/api/v1/billing/change-tier?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"tier": "GROWTH"},
    )
    assert hacked_res.status_code == 403
