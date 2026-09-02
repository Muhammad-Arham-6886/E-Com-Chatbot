import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawling import CrawlJob, CrawlPage, KnowledgeDocument
from app.models.enums import CrawlJobStatusEnum, CrawlPageStatusEnum, DocumentStatusEnum
from app.models.website import Website
from app.services.crawler.content_extractor import ContentExtractor
from app.services.crawler.robots_parser import RobotsParser
from app.services.crawler.sitemap_parser import SitemapParser
from app.services.crawler.ssrf_guard import SSRFGuard, SSRFSecurityException


class CrawlerEngine:
    def __init__(self, db: AsyncSession, crawl_job_id: str, custom_client: Optional[httpx.AsyncClient] = None):
        self.db = db
        self.crawl_job_id = crawl_job_id
        self.custom_client = custom_client

    async def execute(self) -> CrawlJob:
        stmt = select(CrawlJob).where(CrawlJob.id == self.crawl_job_id)
        job = (await self.db.execute(stmt)).scalar_one_or_none()
        if not job:
            raise ValueError(f"Crawl job '{self.crawl_job_id}' not found.")

        # Fetch associated website
        website_stmt = select(Website).where(Website.id == job.website_id)
        website = (await self.db.execute(website_stmt)).scalar_one_or_none()
        if not website:
            job.status = CrawlJobStatusEnum.FAILED
            job.error_message = "Website not found."
            await self.db.commit()
            return job

        job.status = CrawlJobStatusEnum.RUNNING
        job.started_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(job)

        should_close_client = False
        client = self.custom_client
        if client is None:
            client = httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "AICommerceBot/1.0 (+https://ai-commerce.internal/bot)"},
                follow_redirects=True,
            )
            should_close_client = True

        visited_urls: Set[str] = set()
        url_queue: List[tuple[str, str, int]] = []  # (url, discovered_via, depth)

        try:
            # 1. Fetch & Parse robots.txt
            robots_rules = await RobotsParser.fetch_and_parse(website.url, client=client)

            # 2. Discover Sitemaps
            potential_sitemaps = list(robots_rules.sitemaps)
            potential_sitemaps.append(urljoin(website.url, "/sitemap.xml"))
            potential_sitemaps.append(urljoin(website.url, "/sitemap_index.xml"))
            # remove duplicates while preserving order
            sitemaps_to_probe = list(dict.fromkeys(potential_sitemaps))

            sitemap_urls = await SitemapParser.discover_sitemap_urls(
                sitemaps_to_probe, target_domain=website.domain, client=client
            )

            # 3. Seed queue with root URL and sitemap URLs
            url_queue.append((website.url, "root", 0))
            for s_url in sitemap_urls:
                if s_url != website.url:
                    url_queue.append((s_url, "sitemap", 1))

            job.total_pages_discovered = len(url_queue)
            await self.db.commit()

            # 4. Crawl Loop
            while url_queue and job.total_pages_crawled < job.max_pages:
                # Check if job was cancelled
                await self.db.refresh(job)
                if job.status == CrawlJobStatusEnum.CANCELLED:
                    break

                current_url, discovered_via, depth = url_queue.pop(0)
                parsed = urlparse(current_url)
                canonical_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
                if not canonical_url:
                    canonical_url = current_url

                if canonical_url in visited_urls:
                    continue
                visited_urls.add(canonical_url)

                # Enforce domain restriction
                domain = parsed.hostname.lower() if parsed.hostname else ""
                if domain != website.domain and not domain.endswith(f".{website.domain}"):
                    continue

                # Check robots.txt
                if not robots_rules.is_allowed(parsed.path):
                    skipped_page = CrawlPage(
                        crawl_job_id=job.id,
                        website_id=website.id,
                        url=canonical_url,
                        status=CrawlPageStatusEnum.SKIPPED_ROBOTS,
                        discovered_via=discovered_via,
                        depth=depth,
                    )
                    self.db.add(skipped_page)
                    await self.db.commit()
                    continue

                # SSRF Protection
                try:
                    SSRFGuard.validate_url(canonical_url, allow_mock_hosts=(self.custom_client is not None))
                except SSRFSecurityException as e:
                    failed_page = CrawlPage(
                        crawl_job_id=job.id,
                        website_id=website.id,
                        url=canonical_url,
                        status=CrawlPageStatusEnum.FAILED,
                        error=f"SSRF Security Violation: {str(e)}",
                        discovered_via=discovered_via,
                        depth=depth,
                    )
                    self.db.add(failed_page)
                    job.total_pages_failed += 1
                    await self.db.commit()
                    continue

                # Fetch Page with retry
                resp = None
                fetch_error = None
                for attempt in range(2):
                    try:
                        resp = await client.get(canonical_url)
                        if resp.status_code < 500:
                            break
                    except Exception as e:
                        fetch_error = e
                        await asyncio.sleep(0.5)

                if resp is None or resp.status_code >= 400:
                    status_code = resp.status_code if resp else None
                    err_msg = str(fetch_error) if fetch_error else f"HTTP {status_code}"
                    failed_page = CrawlPage(
                        crawl_job_id=job.id,
                        website_id=website.id,
                        url=canonical_url,
                        status=CrawlPageStatusEnum.FAILED,
                        status_code=status_code,
                        error=err_msg,
                        discovered_via=discovered_via,
                        depth=depth,
                    )
                    self.db.add(failed_page)
                    job.total_pages_failed += 1
                    await self.db.commit()
                    continue

                # Extract Content
                try:
                    extracted = ContentExtractor.extract(resp.text, canonical_url, website.domain)

                    # Create CrawlPage record
                    crawl_page = CrawlPage(
                        crawl_job_id=job.id,
                        website_id=website.id,
                        url=canonical_url,
                        status=CrawlPageStatusEnum.CRAWLED,
                        status_code=resp.status_code,
                        page_title=extracted.title,
                        content_hash=extracted.content_hash,
                        discovered_via=discovered_via,
                        depth=depth,
                    )
                    self.db.add(crawl_page)
                    await self.db.flush()

                    # Create or update KnowledgeDocument
                    doc_stmt = select(KnowledgeDocument).where(
                        and_(
                            KnowledgeDocument.website_id == website.id,
                            KnowledgeDocument.url == canonical_url,
                        )
                    )
                    existing_doc = (await self.db.execute(doc_stmt)).scalar_one_or_none()

                    if existing_doc:
                        existing_doc.title = extracted.title
                        existing_doc.meta_description = extracted.meta_description
                        existing_doc.raw_content = extracted.clean_text
                        existing_doc.content_hash = extracted.content_hash
                        existing_doc.token_count = extracted.token_count
                        existing_doc.crawl_page_id = crawl_page.id
                        existing_doc.status = DocumentStatusEnum.RAW
                    else:
                        new_doc = KnowledgeDocument(
                            website_id=website.id,
                            organization_id=website.organization_id,
                            crawl_page_id=crawl_page.id,
                            url=canonical_url,
                            title=extracted.title,
                            meta_description=extracted.meta_description,
                            raw_content=extracted.clean_text,
                            content_hash=extracted.content_hash,
                            token_count=extracted.token_count,
                            status=DocumentStatusEnum.RAW,
                        )
                        self.db.add(new_doc)

                    job.total_pages_crawled += 1

                    # If internal link discovery is enabled, queue new unvisited links
                    for link in extracted.internal_links:
                        if link not in visited_urls and not any(l[0] == link for l in url_queue):
                            url_queue.append((link, "internal_link", depth + 1))
                            job.total_pages_discovered += 1

                    await self.db.commit()

                except Exception as e:
                    failed_page = CrawlPage(
                        crawl_job_id=job.id,
                        website_id=website.id,
                        url=canonical_url,
                        status=CrawlPageStatusEnum.FAILED,
                        status_code=resp.status_code,
                        error=f"Extraction Error: {str(e)}",
                        discovered_via=discovered_via,
                        depth=depth,
                    )
                    self.db.add(failed_page)
                    job.total_pages_failed += 1
                    await self.db.commit()

            # Finalize Crawl Job Status
            await self.db.refresh(job)
            if job.status != CrawlJobStatusEnum.CANCELLED:
                job.status = CrawlJobStatusEnum.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(job)

        except Exception as e:
            job.status = CrawlJobStatusEnum.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
        finally:
            if should_close_client:
                await client.aclose()

        return job
