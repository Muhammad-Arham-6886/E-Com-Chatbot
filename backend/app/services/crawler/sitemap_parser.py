import xml.etree.ElementTree as ET
from typing import List, Set, Optional
from urllib.parse import urlparse, urljoin
import httpx

from app.services.crawler.ssrf_guard import SSRFGuard


class SitemapParser:
    @staticmethod
    def _strip_ns(tag: str) -> str:
        """Helper to remove XML namespaces e.g. '{http://www.sitemaps.org/schemas/sitemap/0.9}loc' -> 'loc'"""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    @classmethod
    def parse_sitemap_xml(cls, xml_text: str, target_domain: str) -> tuple[List[str], List[str]]:
        """
        Parses XML text and returns:
            (page_urls, sub_sitemap_urls)
        Filters URLs to ensure they match target_domain.
        """
        page_urls: List[str] = []
        sub_sitemaps: List[str] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return page_urls, sub_sitemaps

        root_tag = cls._strip_ns(root.tag).lower()

        # Check if sitemap index
        if root_tag == "sitemapindex":
            for sitemap in root:
                for elem in sitemap:
                    if cls._strip_ns(elem.tag).lower() == "loc" and elem.text:
                        loc_url = elem.text.strip()
                        sub_sitemaps.append(loc_url)

        # Check if regular urlset
        elif root_tag == "urlset":
            for url_elem in root:
                for elem in url_elem:
                    if cls._strip_ns(elem.tag).lower() == "loc" and elem.text:
                        loc_url = elem.text.strip()
                        parsed = urlparse(loc_url)
                        domain = parsed.hostname.lower() if parsed.hostname else ""
                        if domain == target_domain or domain.endswith(f".{target_domain}"):
                            page_urls.append(loc_url)

        return page_urls, sub_sitemaps

    @classmethod
    async def discover_sitemap_urls(
        cls,
        sitemap_urls: List[str],
        target_domain: str,
        max_depth: int = 2,
        client: Optional[httpx.AsyncClient] = None,
    ) -> List[str]:
        """
        Recursively fetches and parses sitemaps and nested sitemap indexes.
        Returns a list of discovered page URLs within target_domain.
        """
        discovered_pages: Set[str] = set()
        visited_sitemaps: Set[str] = set()
        sitemaps_to_visit: List[tuple[str, int]] = [(u, 0) for u in sitemap_urls]

        should_close = False
        if client is None:
            client = httpx.AsyncClient(
                timeout=8.0,
                headers={"User-Agent": "AICommerceBot/1.0 (+https://ai-commerce.internal/bot)"},
                follow_redirects=True,
            )
            should_close = True

        try:
            while sitemaps_to_visit:
                current_url, depth = sitemaps_to_visit.pop(0)
                if current_url in visited_sitemaps or depth > max_depth:
                    continue
                visited_sitemaps.add(current_url)

                try:
                    # Validate against SSRF
                    allow_mock = client is not None and not should_close
                    SSRFGuard.validate_url(current_url, allow_mock_hosts=allow_mock)
                    resp = await client.get(current_url)
                    if resp.status_code == 200:
                        pages, nested_sitemaps = cls.parse_sitemap_xml(resp.text, target_domain)
                        for p in pages:
                            discovered_pages.add(p)
                        for ns in nested_sitemaps:
                            if ns not in visited_sitemaps:
                                sitemaps_to_visit.append((ns, depth + 1))
                except Exception:
                    continue
        finally:
            if should_close:
                await client.aclose()

        return list(discovered_pages)
