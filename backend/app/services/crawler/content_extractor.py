import hashlib
import re
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Comment


class ExtractedContent:
    def __init__(
        self,
        title: str,
        meta_description: Optional[str],
        clean_text: str,
        content_hash: str,
        token_count: int,
        internal_links: List[str],
    ):
        self.title = title
        self.meta_description = meta_description
        self.clean_text = clean_text
        self.content_hash = content_hash
        self.token_count = token_count
        self.internal_links = internal_links


class ContentExtractor:
    UNWANTED_TAGS = {
        "script", "style", "noscript", "svg", "iframe", "form",
        "input", "button", "select", "textarea", "dialog", "canvas",
        "audio", "video", "nav", "footer", "header", "aside",
    }

    UNWANTED_SELECTORS = [
        # General noise
        '[class*="cookie"]', '[id*="cookie"]',
        '[class*="popup"]', '[id*="popup"]',
        '[class*="modal"]', '[id*="modal"]',
        '[class*="banner"]', '[class*="advertisement"]',
        '[class*="disclaimer"]',
        # Navigation & menus
        '[class*="nav-"]', '[class*="-nav"]', '[class*="menu"]',
        '[class*="sidebar"]', '[class*="side-bar"]',
        '[class*="breadcrumb"]', '[class*="breadcrumb"]',
        '[class*="pagination"]', '[class*="pager"]',
        # E-commerce noise
        '[class*="category-list"]', '[class*="category-menu"]',
        '[class*="product-filter"]', '[class*="filter-"]',
        '[class*="catalog-nav"]', '[class*="shop-nav"]',
        '[class*="top-bar"]', '[class*="header-links"]',
        '[class*="related-products"]', '[class*="recently-viewed"]',
        '[class*="product-grid"]', '[class*="product-list"]',
        # Footer & legal
        '[class*="footer"]', '[id*="footer"]',
        '[class*="legal"]', '[class*="copyright"]',
        # Social & sharing
        '[class*="social"]', '[class*="share"]', '[class*="follow"]',
        # Comments & reviews widgets
        '[class*="comment-section"]', '[id*="comments"]',
    ]

    # Short navigation-like phrases to filter out
    NAVIGATION_PATTERNS = [
        r'^(home|shop|about|contact|blog|faq|login|register|cart|checkout|account)\s*$',
        r'^(add to basket|add to cart|buy now|view cart)\s*$',
        r'^(previous|next|back|forward|page \d+)\s*$',
        r'^\d+\s*$',  # Just a number
        r'^[A-Z][a-z]+$',  # Single capitalized word (category name)
    ]

    @classmethod
    def _is_navigation_text(cls, text: str) -> bool:
        """Check if text is likely navigation/menu content."""
        text = text.strip()
        if len(text) < 3:
            return True
        for pattern in cls.NAVIGATION_PATTERNS:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False

    @classmethod
    def _find_content_root(cls, soup: BeautifulSoup):
        """Find the main content container, avoiding navigation/sidebars."""
        # Try semantic HTML5 elements first
        for tag in ["article", "main", "[role='main']"]:
            root = soup.select_one(tag)
            if root:
                return root

        # Try common content class/id patterns
        content_selectors = [
            '[class*="content"]', '[id*="content"]',
            '[class*="product-description"]', '[class*="product-info"]',
            '[class*="product-detail"]', '[class*="single-product"]',
            '[class*="entry-content"]', '[class*="post-content"]',
            '[class*="page-content"]', '[class*="main-content"]',
        ]
        for sel in content_selectors:
            root = soup.select_one(sel)
            if root and len(root.get_text(strip=True)) > 100:
                return root

        # Fallback: find the div with the most <p> children
        best_div = None
        best_p_count = 0
        for div in soup.find_all("div"):
            p_count = len(div.find_all("p"))
            if p_count > best_p_count:
                best_p_count = p_count
                best_div = div
        if best_div and best_p_count >= 2:
            return best_div

        return soup.body or soup

    @classmethod
    def extract(cls, html: str, base_url: str, target_domain: str) -> ExtractedContent:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract Internal Links before stripping tags
        internal_links: Set[str] = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            clean_host = parsed.hostname.lower() if parsed.hostname else ""
            if clean_host == target_domain or clean_host.endswith(f".{target_domain}"):
                if not re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|zip|tar|gz|mp3|mp4|avi|exe|dmg)$", parsed.path, re.I):
                    internal_links.add(clean_url.rstrip("/"))

        # 2. Extract Title
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()
        if not title:
            og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "og:title"})
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
        if not title:
            h1_tag = soup.find("h1")
            if h1_tag:
                title = h1_tag.get_text().strip()
        if not title:
            title = "Untitled Page"

        # 3. Extract Meta Description
        meta_desc: Optional[str] = None
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag["content"].strip()

        # 4. Strip Comments
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()

        # 5. Strip Unwanted Tags
        for tag_name in cls.UNWANTED_TAGS:
            for element in soup.find_all(tag_name):
                element.decompose()

        # 6. Strip Unwanted Selectors
        for selector in cls.UNWANTED_SELECTORS:
            try:
                for element in soup.select(selector):
                    element.decompose()
            except Exception:
                pass

        # 7. Find content root and extract text
        content_root = cls._find_content_root(soup)

        lines = []
        # Extract from content root only
        for elem in content_root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            text = elem.get_text(separator=" ", strip=True)
            if len(text) > 15 and text not in lines and not cls._is_navigation_text(text):
                lines.append(text)

        # Also extract <li> from content root ONLY (not navigation)
        for elem in content_root.find_all("li"):
            parent = elem.parent
            # Skip <li> inside nav, header, footer, aside, or sidebar
            if parent and parent.name in ("nav", "header", "footer", "aside"):
                continue
            # Skip if parent has navigation-like classes
            parent_classes = " ".join(parent.get("class", [])) if parent else ""
            if any(x in parent_classes.lower() for x in ["nav", "menu", "sidebar", "filter", "category", "breadcrumb"]):
                continue
            text = elem.get_text(separator=" ", strip=True)
            if len(text) > 15 and text not in lines and not cls._is_navigation_text(text):
                lines.append(text)

        # Fallback: use paragraph text from body if nothing found
        if not lines:
            body = soup.body or soup
            for elem in body.find_all("p"):
                text = elem.get_text(separator=" ", strip=True)
                if len(text) > 20 and text not in lines:
                    lines.append(text)

        # Last resort: full body text, filtered
        if not lines:
            full_text = soup.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in full_text.splitlines()
                     if len(l.strip()) > 20 and not cls._is_navigation_text(l.strip())]

        clean_text = "\n\n".join(lines)
        clean_text = re.sub(r"[ \t]+", " ", clean_text)
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

        # 8. Compute Content Hash & Estimated Token Count
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        word_count = len(clean_text.split())
        token_count = int(word_count * 1.33)

        return ExtractedContent(
            title=title[:510],
            meta_description=meta_desc[:1000] if meta_desc else None,
            clean_text=clean_text,
            content_hash=content_hash,
            token_count=token_count,
            internal_links=list(internal_links),
        )
