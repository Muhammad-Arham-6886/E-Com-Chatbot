# Website Crawling & Content Discovery Engine (Phase 3)

The **AI Customer & Commerce Assistant** crawling system is a high-performance, asynchronous pipeline built with Python, Celery, Redis, and BeautifulSoup. It securely discovers and indexes customer websites into clean, searchable knowledge documents for downstream AI RAG search and local model inference.

---

## 1. Architecture Overview

```
[ Dashboard UI / API ]
       │
       ▼  (POST /api/v1/crawling/websites/{id}/start)
[ FastAPI Controller ] ──▶ Creates CrawlJob (PENDING)
       │
       ▼  (Celery dispatch / Background Task)
[ Celery Worker ]
       │
       ├─▶ [ SSRF Guard ] ───────── (Validates scheme, hostname, IP blocklist)
       │
       ├─▶ [ Robots Parser ] ────── (Parses /robots.txt rules & sitemaps)
       │
       ├─▶ [ Sitemap Parser ] ───── (Recursively extracts XML & Index sitemaps)
       │
       ├─▶ [ Queue & Traversal ] ── (Canonicalizes URLs, restricts to domain)
       │
       ├─▶ [ HTTP Fetcher ] ─────── (2x retry on transient failures, timeouts)
       │
       ├─▶ [ Content Extractor ] ── (Strips scripts, styles, navs, footers, ads)
       │
       ▼
[ Database Persistence ]
       ├─ CrawlJob (total_discovered, total_crawled, total_failed, status)
       ├─ CrawlPage (URL, status, HTTP code, discovery source, content_hash)
       └─ KnowledgeDocument (URL, title, clean_text, SHA-256 hash, token_count)
```

---

## 2. SSRF Protection & Security Rules

To prevent Server-Side Request Forgery (SSRF) and cloud metadata exfiltration, every outbound HTTP request must strictly pass `SSRFGuard.validate_url()`:

1. **Protocol Restrictions**: Only `http://` and `https://` are permitted. Schemes like `file://`, `gopher://`, `ftp://` are rejected immediately.
2. **Blocked Hostnames**: `localhost`, `localhost.localdomain`, `metadata.google.internal`, `instance-data`.
3. **DNS Resolution & Subnet Blocklist**:
   - Loopback: `127.0.0.0/8`, `::1`
   - RFC 1918 Private Ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
   - Link-Local & Cloud Metadata: `169.254.0.0/16` (including `169.254.169.254`), `fe80::/10`
   - Shared Address Space: `100.64.0.0/10`
   - Multicast & Reserved: `224.0.0.0/4`, `240.0.0.0/4`, `ff00::/8`
   - IPv6 Unique Local: `fc00::/7`

---

## 3. Robots.txt & Sitemap Discovery

1. **Robots.txt Parser (`RobotsParser`)**:
   - Safely fetches `/robots.txt`.
   - Parses `User-agent:` rules (evaluating bot agent or `*`).
   - Respects `Disallow:` and `Allow:` rules (longer allow paths override disallow).
   - Extracts `Crawl-delay` and `Sitemap:` directives.
2. **Sitemap Parser (`SitemapParser`)**:
   - Parses `<urlset><url><loc>` standard XML sitemaps.
   - Parses `<sitemapindex><sitemap><loc>` sitemap trees recursively up to max depth.
   - Filters all discovered URLs against the target website domain.

---

## 4. Content Sanitization & Extraction

The `ContentExtractor` strips layout clutter and extracts clean, readable text:

- **Stripped Noise**:
  - Tags: `<script>`, `<style>`, `<noscript>`, `<svg>`, `<iframe>`, `<form>`, `<button>`, `<input>`, `<dialog>`, `<nav>`, `<footer>`, `<header>`, `<aside>`.
  - CSS Selectors: Cookie consent banners, popup modals, ad containers, footer wrappers, navigation bars.
- **Extracted Attributes**:
  - `title`: `<title>`, `og:title`, or `<h1>`.
  - `meta_description`: `<meta name="description">` or `og:description`.
  - `clean_text`: Headings (`h1`-`h6`), `<p>`, `<li>`, `<article>`, `<section>` blocks with whitespace normalization.
  - `content_hash`: SHA-256 checksum for change tracking and incremental sync.
  - `token_count`: Estimated LLM token count (`word_count * 1.33`).
  - `internal_links`: In-domain URLs discovered for recursive queue traversal.

---

## 5. REST API Endpoints

| Method | Endpoint | Description | Min Role |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/crawling/websites/{website_id}/start?org_id=...` | Start background web crawl job | `ADMIN` |
| `GET` | `/api/v1/crawling/jobs/{job_id}?org_id=...` | Get job progress and status | `VIEWER` |
| `POST` | `/api/v1/crawling/jobs/{job_id}/cancel?org_id=...` | Cancel active crawl job | `ADMIN` |
| `GET` | `/api/v1/crawling/websites/{website_id}/pages?org_id=...` | List discovered/crawled pages | `VIEWER` |
| `GET` | `/api/v1/crawling/websites/{website_id}/documents?org_id=...` | List extracted knowledge documents | `VIEWER` |
