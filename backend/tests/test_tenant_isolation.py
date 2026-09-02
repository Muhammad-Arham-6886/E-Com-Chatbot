import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_organization_creation_and_owner_assignment(client: AsyncClient, create_test_user):
    user_a, token_a = await create_test_user("usera@example.com")

    # Create Org A
    res = await client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Acme Corp", "slug": "acme-corp"},
    )
    assert res.status_code == 201
    org_a = res.json()
    assert org_a["name"] == "Acme Corp"
    assert org_a["slug"] == "acme-corp"

    # Verify User A is listed with OWNER role
    orgs_res = await client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert orgs_res.status_code == 200
    user_orgs = orgs_res.json()
    assert len(user_orgs) == 1
    assert user_orgs[0]["id"] == org_a["id"]
    assert user_orgs[0]["role"] == "OWNER"


@pytest.mark.asyncio
async def test_strict_tenant_isolation_cross_access_blocked(
    client: AsyncClient, create_test_user, create_test_org
):
    # Setup Tenant A and Tenant B
    user_a, token_a = await create_test_user("tenant_a_owner@example.com")
    user_b, token_b = await create_test_user("tenant_b_owner@example.com")

    org_a = await create_test_org("Tenant A Org", user_a)
    org_b = await create_test_org("Tenant B Org", user_b)

    # 1. User A tries to read Org B details
    res_read = await client.get(
        f"/api/v1/organizations/{org_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_read.status_code == 403
    assert "access" in res_read.json()["detail"].lower()

    # 2. User A tries to update Org B details
    res_update = await client.put(
        f"/api/v1/organizations/{org_b.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Hacked Org B"},
    )
    assert res_update.status_code == 403

    # 3. User A tries to list Org B members
    res_members = await client.get(
        f"/api/v1/organizations/{org_b.id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_members.status_code == 403

    # 4. User A tries to invite a user into Org B
    res_invite = await client.post(
        f"/api/v1/organizations/{org_b.id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"email": "intruder@example.com", "role": "ADMIN"},
    )
    assert res_invite.status_code == 403

    # 5. User A's organization list must ONLY contain Org A
    orgs_a = await client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert orgs_a.status_code == 200
    ids_a = [o["id"] for o in orgs_a.json()]
    assert org_a.id in ids_a
    assert org_b.id not in ids_a
