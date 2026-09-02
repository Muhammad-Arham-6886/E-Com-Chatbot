import pytest
from httpx import AsyncClient
from app.models.enums import RoleEnum, MembershipStatus, PlatformEnum, WebsiteStatusEnum
from app.models.organization import OrganizationMember
from app.services.platform_detector import PlatformDetector


@pytest.mark.asyncio
async def test_platform_detector_normalization():
    norm_url, domain = PlatformDetector.normalize_url("https://www.example.com/shop/page?ref=1")
    assert norm_url == "https://www.example.com"
    assert domain == "example.com"

    norm_url2, domain2 = PlatformDetector.normalize_url("myshop.store:8080")
    assert norm_url2 == "https://myshop.store:8080"
    assert domain2 == "myshop.store"

    with pytest.raises(ValueError):
        PlatformDetector.normalize_url("")


@pytest.mark.asyncio
async def test_create_website_and_defaults(client: AsyncClient, create_test_user, create_test_org):
    user, token = await create_test_user("webmaster@example.com")
    org = await create_test_org("Webmaster Org", user)

    payload = {
        "name": "My Shopify Store",
        "url": "https://store.example.com/products",
    }
    res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "My Shopify Store"
    assert data["url"] == "https://store.example.com"
    assert data["domain"] == "store.example.com"
    assert data["public_site_id"].startswith("site_")
    assert data["settings"] is not None
    assert data["settings"]["chatbot_name"] == "My Shopify Store Assistant"
    assert data["settings"]["primary_color"] == "#4F46E5"
    assert len(data["domains"]) == 1
    assert data["domains"][0]["domain"] == "store.example.com"


@pytest.mark.asyncio
async def test_list_websites_by_organization(client: AsyncClient, create_test_user, create_test_org):
    user, token = await create_test_user("multisite@example.com")
    org = await create_test_org("MultiSite Corp", user)

    # Add 2 websites
    await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Site One", "url": "https://siteone.com"},
    )
    await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Site Two", "url": "https://sitetwo.com"},
    )

    res = await client.get(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    websites = res.json()
    assert len(websites) == 2
    domains = [w["domain"] for w in websites]
    assert "siteone.com" in domains
    assert "sitetwo.com" in domains


@pytest.mark.asyncio
async def test_strict_tenant_isolation_websites(client: AsyncClient, create_test_user, create_test_org):
    user_a, token_a = await create_test_user("owner_a@example.com")
    user_b, token_b = await create_test_user("owner_b@example.com")

    org_a = await create_test_org("Org A", user_a)
    org_b = await create_test_org("Org B", user_b)

    # Create website in Org A
    res_a = await client.post(
        f"/api/v1/websites?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Org A Site", "url": "https://orga.com"},
    )
    assert res_a.status_code == 201
    site_a_id = res_a.json()["id"]

    # 1. User B tries to view Org A's website
    res_b_view = await client.get(
        f"/api/v1/websites/{site_a_id}?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_view.status_code == 403

    # 2. User B tries to view with their own org_id
    res_b_view_own_org = await client.get(
        f"/api/v1/websites/{site_a_id}?org_id={org_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_view_own_org.status_code == 404

    # 3. User B tries to update Org A's website
    res_b_update = await client.put(
        f"/api/v1/websites/{site_a_id}?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"name": "Hacked Site"},
    )
    assert res_b_update.status_code == 403

    # 4. User B tries to delete Org A's website
    res_b_delete = await client.delete(
        f"/api/v1/websites/{site_a_id}?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_delete.status_code == 403


@pytest.mark.asyncio
async def test_website_rbac_permissions(
    client: AsyncClient, create_test_user, create_test_org, db_session
):
    owner, owner_token = await create_test_user("site_owner@example.com")
    viewer, viewer_token = await create_test_user("site_viewer@example.com")
    org = await create_test_org("RBAC Org", owner)

    # Add viewer to org
    viewer_member = OrganizationMember(
        organization_id=org.id,
        user_id=viewer.id,
        role=RoleEnum.VIEWER,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(viewer_member)
    await db_session.commit()

    # Create website as OWNER
    res_create = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "RBAC Test Site", "url": "https://rbacsite.com"},
    )
    assert res_create.status_code == 201
    site_id = res_create.json()["id"]

    # VIEWER CAN view website
    res_view = await client.get(
        f"/api/v1/websites/{site_id}?org_id={org.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_view.status_code == 200

    # VIEWER CANNOT update website
    res_update = await client.put(
        f"/api/v1/websites/{site_id}?org_id={org.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"name": "Viewer Rename"},
    )
    assert res_update.status_code == 403

    # VIEWER CANNOT update settings
    res_settings_update = await client.put(
        f"/api/v1/websites/{site_id}/settings?org_id={org.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"primary_color": "#000000"},
    )
    assert res_settings_update.status_code == 403

    # VIEWER CANNOT delete website
    res_del = await client.delete(
        f"/api/v1/websites/{site_id}?org_id={org.id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert res_del.status_code == 403


@pytest.mark.asyncio
async def test_website_settings_and_public_config(client: AsyncClient, create_test_user, create_test_org):
    user, token = await create_test_user("customizer@example.com")
    org = await create_test_org("Brand Org", user)

    # 1. Create site
    create_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Brand Shop", "url": "https://brandshop.com"},
    )
    assert create_res.status_code == 201
    site = create_res.json()
    site_id = site["id"]
    public_id = site["public_site_id"]

    # 2. Update widget settings
    settings_payload = {
        "chatbot_name": "Brand Assistant Pro",
        "welcome_message": "Welcome to Brand Shop! How can we assist?",
        "primary_color": "#10B981",
        "secondary_color": "#064E3B",
        "launcher_position": "bottom-left",
        "enable_whatsapp": True,
        "whatsapp_number": "+1234567890",
    }
    settings_res = await client.put(
        f"/api/v1/websites/{site_id}/settings?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json=settings_payload,
    )
    assert settings_res.status_code == 200
    updated_settings = settings_res.json()
    assert updated_settings["chatbot_name"] == "Brand Assistant Pro"
    assert updated_settings["primary_color"] == "#10B981"
    assert updated_settings["launcher_position"] == "bottom-left"

    # 3. Verify public unauthenticated endpoint returns updated widget configuration
    pub_res = await client.get(f"/api/v1/websites/public/{public_id}/config")
    assert pub_res.status_code == 200
    pub_config = pub_res.json()
    assert pub_config["public_site_id"] == public_id
    assert pub_config["chatbot_name"] == "Brand Assistant Pro"
    assert pub_config["primary_color"] == "#10B981"
    assert pub_config["launcher_position"] == "bottom-left"
    assert pub_config["enable_whatsapp"] is True
    assert pub_config["whatsapp_number"] == "+1234567890"
