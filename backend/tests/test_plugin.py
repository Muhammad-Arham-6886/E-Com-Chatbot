import io
import zipfile
import pytest
from httpx import AsyncClient
from app.models.website import Website
from app.services.plugin_service import WordPressPluginService


def test_generate_plugin_zip_structure():
    mock_website = Website(
        id="mock_site_123",
        name="Test Store",
        domain="teststore.com",
        public_site_id="site_pub_abc123xyz",
    )
    zip_bytes = WordPressPluginService.generate_plugin_zip(mock_website, "https://api.myapp.com")
    assert len(zip_bytes) > 0

    # Parse zip in-memory
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        names = z.namelist()
        assert any("ai-commerce-assistant.php" in name for name in names)
        assert any("class-settings.php" in name for name in names)
        assert any("class-widget-embed.php" in name for name in names)
        
        # Verify pre-configured site id is injected into main file
        main_php = z.read("ai-commerce-assistant/ai-commerce-assistant.php").decode("utf-8")
        assert "site_pub_abc123xyz" in main_php
        assert "https://api.myapp.com" in main_php


@pytest.mark.asyncio
async def test_download_wordpress_plugin_endpoint(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user, token = await create_test_user("wp_dev@example.com")
    org = await create_test_org("WP Plugin Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "WP Shop", "url": "https://wpshop.com"},
    )
    website_id = site_res.json()["id"]

    # Download Plugin ZIP
    dl_res = await client.get(
        f"/api/v1/websites/{website_id}/download-plugin?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"
    assert "ai-commerce-assistant-wpshop-com.zip" in dl_res.headers["content-disposition"]

    # Verify received content is valid zip
    with zipfile.ZipFile(io.BytesIO(dl_res.content), "r") as z:
        assert "ai-commerce-assistant/ai-commerce-assistant.php" in z.namelist()


@pytest.mark.asyncio
async def test_strict_tenant_isolation_plugin_download(
    client: AsyncClient,
    create_test_user,
    create_test_org,
):
    user_a, token_a = await create_test_user("user_a_wp@example.com")
    org_a = await create_test_org("Org A WP", user_a)

    user_b, token_b = await create_test_user("user_b_wp@example.com")
    org_b = await create_test_org("Org B WP", user_b)

    site_a = await client.post(
        f"/api/v1/websites?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Secret WP Store", "url": "https://secret-wp.com"},
    )
    site_a_id = site_a.json()["id"]

    # User B tries to download Org A's plugin ZIP with Org A ID -> 403
    res_b = await client.get(
        f"/api/v1/websites/{site_a_id}/download-plugin?org_id={org_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 403

    # User B tries with Org B ID -> 404
    res_b2 = await client.get(
        f"/api/v1/websites/{site_a_id}/download-plugin?org_id={org_b.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b2.status_code == 404
