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
        "script",
        "style",
        "noscript",
        "svg",
        "iframe",
        "form",
        "input",
        "button",
        "select",
        "textarea",
        "dialog",
        "canvas",
        "audio",
        "video",
        "nav",
        "footer",
        "header",
        "aside",
    }

    UNWANTED_SELECTORS = [
        '[class*="cookie"]',
        '[id*="cookie"]',
        '[class*="popup"]',
        '[id*="popup"]',
        '[class*="modal"]',
        '[id*="modal"]',
        '[class*="banner"]',
        '[class*="advertisement"]',
        '[class*="disclaimer"]',
        '[class*="nav-"]',
        '[class*="footer-"]',
    ]

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

            # Strip fragments and standard query parameters if tracking
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            clean_host = parsed.hostname.lower() if parsed.hostname else ""

            if clean_host == target_domain or clean_host.endswith(f".{target_domain}"):
                # Check for non-HTML extensions
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

        # 7. Extract Clean Text Blocks
        # Process headings and paragraphs
        lines = []
        for elem in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "article", "section"]):
            text = elem.get_text(separator=" ", strip=True)
            if len(text) > 5 and text not in lines:
                lines.append(text)

        if not lines:
            # Fallback to full body text if specific elements are sparse
            full_text = soup.get_text(separator="\n", strip=True)
            lines = [l.strip() for l in full_text.splitlines() if len(l.strip()) > 5]

        clean_text = "\n\n".join(lines)
        # Normalize excessive whitespace
        clean_text = re.sub(r"[ \t]+", " ", clean_text)
        clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

        # 8. Compute Content Hash & Estimated Token Count
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
        word_count = len(clean_text.split())
        token_count = int(word_count * 1.33)  # Standard approximation: 1 token ≈ 0.75 words

        return ExtractedContent(
            title=title[:510],
            meta_description=meta_desc[:1000] if meta_desc else None,
            clean_text=clean_text,
            content_hash=content_hash,
            token_count=token_count,
            internal_links=list(internal_links),
        )
