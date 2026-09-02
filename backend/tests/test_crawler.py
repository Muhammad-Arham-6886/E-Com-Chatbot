import pytest
import httpx
from httpx import AsyncClient, MockTransport, Response
from app.models.enums import CrawlJobStatusEnum, CrawlPageStatusEnum, DocumentStatusEnum
from app.models.crawling import CrawlJob
from app.services.crawler.ssrf_guard import SSRFGuard, SSRFSecurityException
from app.services.crawler.robots_parser import RobotsParser
from app.services.crawler.sitemap_parser import SitemapParser
from app.services.crawler.content_extractor import ContentExtractor
from app.services.crawler.crawler_engine import CrawlerEngine


def test_ssrf_guard_blocks_forbidden_ips_and_hosts():
    # 1. Block localhost and loopback
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://localhost/admin")
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://127.0.0.1:8000/api")
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://[::1]/secret")

    # 2. Block RFC1918 Private Ranges
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://10.0.0.1/internal")
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://192.168.1.100/router")
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://172.16.5.4/dashboard")

    # 3. Block Cloud Metadata Endpoints
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://169.254.169.254/latest/meta-data")
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("http://metadata.google.internal/computeMetadata/v1/")

    # 4. Block Invalid Schemes
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("file:///etc/passwd")
    with pytest.raises(SSRFSecurityException):
        SSRFGuard.validate_url("ftp://example.com/file")


def test_robots_parser_rules():
    sample_robots = """
    User-agent: *
    Disallow: /admin/
    Disallow: /checkout
    Disallow: /private/
    Allow: /admin/public
    Crawl-delay: 2
    Sitemap: https://example.com/sitemap.xml
    Sitemap: https://example.com/news-sitemap.xml
    """

    rules = RobotsParser.parse_robots_text(sample_robots, user_agent="*", base_url="https://example.com")
    assert rules.is_allowed("/") is True
    assert rules.is_allowed("/products/item-1") is True
    assert rules.is_allowed("/admin/dashboard") is False
    assert rules.is_allowed("/admin/public") is True  # Allow rule overrides
    assert rules.is_allowed("/checkout") is False
    assert rules.crawl_delay == 2.0
    assert len(rules.sitemaps) == 2
    assert "https://example.com/sitemap.xml" in rules.sitemaps


def test_sitemap_parser_xml_and_indexes():
    # 1. Test regular urlset
    urlset_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://mysite.com/</loc></url>
        <url><loc>https://mysite.com/about</loc></url>
        <url><loc>https://mysite.com/products</loc></url>
        <url><loc>https://external-site.com/spam</loc></url>
    </urlset>"""

    pages, sub_sitemaps = SitemapParser.parse_sitemap_xml(urlset_xml, target_domain="mysite.com")
    assert len(pages) == 3
    assert "https://mysite.com/about" in pages
    assert "https://external-site.com/spam" not in pages
    assert len(sub_sitemaps) == 0

    # 2. Test sitemap index
    sitemap_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap><loc>https://mysite.com/post-sitemap.xml</loc></sitemap>
        <sitemap><loc>https://mysite.com/page-sitemap.xml</loc></sitemap>
    </sitemapindex>"""

    pages2, sub_sitemaps2 = SitemapParser.parse_sitemap_xml(sitemap_index_xml, target_domain="mysite.com")
    assert len(pages2) == 0
    assert len(sub_sitemaps2) == 2
    assert "https://mysite.com/post-sitemap.xml" in sub_sitemaps2


def test_content_extractor_cleans_html():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Acme Widgets - Premium E-Commerce</title>
        <meta name="description" content="We sell the highest quality widgets online.">
        <script>console.log("tracking code");</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <header>
            <nav class="nav-bar">
                <a href="/">Home</a>
                <a href="/pricing">Pricing</a>
                <a href="https://external.com">External Link</a>
            </nav>
        </header>

        <div class="cookie-banner">Accept our cookies!</div>

        <main>
            <h1>Welcome to Acme Widgets</h1>
            <p>Our widgets are engineered with aerospace grade materials.</p>
            <p>Order today and get free shipping across the country.</p>
            <a href="/catalog/gear-1">View Gear 1</a>
        </main>

        <footer class="footer-section">
            <p>&copy; 2026 Acme Corp. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """

    extracted = ContentExtractor.extract(sample_html, base_url="https://acme.com", target_domain="acme.com")
    assert extracted.title == "Acme Widgets - Premium E-Commerce"
    assert extracted.meta_description == "We sell the highest quality widgets online."
    assert "tracking code" not in extracted.clean_text
    assert "Accept our cookies" not in extracted.clean_text
    assert "Welcome to Acme Widgets" in extracted.clean_text
    assert "aerospace grade materials" in extracted.clean_text
    assert len(extracted.content_hash) == 64
    assert extracted.token_count > 5
    assert "https://acme.com/catalog/gear-1" in extracted.internal_links
    assert "https://external.com" not in extracted.internal_links


@pytest.mark.asyncio
async def test_crawler_engine_end_to_end_mocked(client: AsyncClient, create_test_user, create_test_org, db_session):
    user, token = await create_test_user("crawler_admin@example.com")
    org = await create_test_org("Crawl Org", user)

    # 1. Create website
    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Mock Store", "url": "https://mockstore.local"},
    )
    assert site_res.status_code == 201
    website_id = site_res.json()["id"]

    # 2. Create mock HTTP transport
    mock_robots = "User-agent: *\nDisallow: /secret\nSitemap: https://mockstore.local/sitemap.xml\n"
    mock_sitemap = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://mockstore.local/</loc></url>
        <url><loc>https://mockstore.local/about</loc></url>
        <url><loc>https://mockstore.local/products</loc></url>
    </urlset>"""
    mock_home_html = "<html><head><title>Mock Store Home</title></head><body><h1>Welcome</h1><p>Home content text.</p><a href='/contact'>Contact Us</a></body></html>"
    mock_about_html = "<html><head><title>About Mock Store</title></head><body><h1>About Us</h1><p>About content description.</p></body></html>"
    mock_products_html = "<html><head><title>Product Catalog</title></head><body><h1>Our Products</h1><p>Catalog list.</p></body></html>"
    mock_contact_html = "<html><head><title>Contact Support</title></head><body><h1>Contact Us</h1><p>Email us at support@mockstore.local</p></body></html>"

    def mock_handler(request: httpx.Request):
        url = str(request.url).rstrip("/")
        if url == "https://mockstore.local/robots.txt":
            return Response(200, text=mock_robots)
        elif url == "https://mockstore.local/sitemap.xml":
            return Response(200, text=mock_sitemap)
        elif url == "https://mockstore.local":
            return Response(200, text=mock_home_html)
        elif url == "https://mockstore.local/about":
            return Response(200, text=mock_about_html)
        elif url == "https://mockstore.local/products":
            return Response(200, text=mock_products_html)
        elif url == "https://mockstore.local/contact":
            return Response(200, text=mock_contact_html)
        return Response(404, text="Not Found")

    mock_client = httpx.AsyncClient(transport=MockTransport(mock_handler))

    # 3. Create CrawlJob in DB
    job = CrawlJob(
        website_id=website_id,
        organization_id=org.id,
        status=CrawlJobStatusEnum.PENDING,
        max_pages=10,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # 4. Run CrawlerEngine with mock client
    engine = CrawlerEngine(db_session, job.id, custom_client=mock_client)
    finished_job = await engine.execute()

    assert finished_job.status == CrawlJobStatusEnum.COMPLETED
    assert finished_job.total_pages_crawled >= 3
    assert finished_job.total_pages_failed == 0

    # 5. Verify API endpoints for crawled pages & documents
    pages_res = await client.get(
        f"/api/v1/crawling/websites/{website_id}/pages?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pages_res.status_code == 200
    pages_data = pages_res.json()
    assert len(pages_data) >= 3

    docs_res = await client.get(
        f"/api/v1/crawling/websites/{website_id}/documents?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert docs_res.status_code == 200
    docs_data = docs_res.json()
    assert len(docs_data) >= 3
    titles = [d["title"] for d in docs_data]
    assert "Mock Store Home" in titles
    assert "About Mock Store" in titles


@pytest.mark.asyncio
async def test_crawling_api_endpoints(client: AsyncClient, create_test_user, create_test_org):
    user, token = await create_test_user("crawler_api_user@example.com")
    org = await create_test_org("API Org", user)

    site_res = await client.post(
        f"/api/v1/websites?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "API Site", "url": "https://apisite.com"},
    )
    site_id = site_res.json()["id"]

    # 1. Start crawl job
    start_res = await client.post(
        f"/api/v1/crawling/websites/{site_id}/start?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_pages": 25},
    )
    assert start_res.status_code == 201
    job_id = start_res.json()["id"]
    assert start_res.json()["max_pages"] == 25

    # 2. Get crawl job status
    status_res = await client.get(
        f"/api/v1/crawling/jobs/{job_id}?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["id"] == job_id

    # 3. Cancel crawl job
    cancel_res = await client.post(
        f"/api/v1/crawling/jobs/{job_id}/cancel?org_id={org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
