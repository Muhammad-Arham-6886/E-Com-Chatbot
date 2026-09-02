# API Reference - AI Customer & Commerce Assistant

## Base URLs
- Local Development: `http://localhost:8000/api/v1`
- OpenAPI Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## System Endpoints
- `GET /health`: Healthcheck endpoint (liveness).
- `GET /ready`: Readiness probe checking database and Redis connections.

## Authentication (`/api/v1/auth`)
- `POST /register`: Register a new user.
- `POST /login`: Authenticate and receive JWT.
- `POST /logout`: Invalidate session/sign out.
- `GET /me`: Get authenticated user profile.

## Organizations (`/api/v1/organizations`)
- `POST /`: Create an organization (creator is assigned `OWNER`).
- `GET /`: List all organizations user is a member of.
- `GET /{org_id}`: Get specific organization details (Requires membership).
- `PUT /{org_id}`: Update organization details (Requires `OWNER` or `ADMIN`).
- `GET /{org_id}/members`: List organization members.
- `POST /{org_id}/members`: Invite or add user to organization (Requires `OWNER` or `ADMIN`).
- `PUT /{org_id}/members/{user_id}`: Update member role (Requires `OWNER` or `ADMIN`).
- `DELETE /{org_id}/members/{user_id}`: Remove member from organization (Requires `OWNER` or `ADMIN`).

## Websites (`/api/v1/websites`)
- `POST /?org_id={org_id}`: Add a new website to an organization (Requires `OWNER` or `ADMIN`).
- `GET /?org_id={org_id}`: List all websites in an organization (Requires `VIEWER`+).
- `GET /{website_id}?org_id={org_id}`: Get detailed website information, settings, and domains.
- `PUT /{website_id}?org_id={org_id}`: Update website name, URL, or status (Requires `OWNER` or `ADMIN`).
- `DELETE /{website_id}?org_id={org_id}`: Delete a website and all its settings (Requires `OWNER` or `ADMIN`).
- `GET /{website_id}/settings?org_id={org_id}`: Get widget appearance settings for a website.
- `PUT /{website_id}/settings?org_id={org_id}`: Update widget appearance settings (Requires `OWNER` or `ADMIN`).
- `POST /{website_id}/detect-platform?org_id={org_id}`: Run live platform detection scan on target URL (Requires `OWNER` or `ADMIN`).
- `GET /public/{public_site_id}/config`: Public unauthenticated endpoint for JS widget to fetch UI configuration.

## Website Crawling & Discovery (`/api/v1/crawling`)
- `POST /websites/{website_id}/start?org_id={org_id}`: Trigger asynchronous website crawl and content discovery job (Requires `ADMIN`+).
- `GET /jobs/{job_id}?org_id={org_id}`: Poll crawl job progress, pages discovered, crawled, and failed counts (Requires `VIEWER`+).
- `POST /jobs/{job_id}/cancel?org_id={org_id}`: Cancel an in-progress crawl job (Requires `ADMIN`+).
- `GET /websites/{website_id}/pages?org_id={org_id}`: List all discovered/crawled URLs and HTTP statuses for a website.
- `GET /websites/{website_id}/documents?org_id={org_id}`: List all sanitized knowledge documents extracted for downstream AI indexing.

## Knowledge Base, Embeddings & Vector Search (`/api/v1/knowledge`)
- `POST /websites/{website_id}/process-embeddings?org_id={org_id}`: Chunk and generate 768-d embeddings for website knowledge documents (Requires `ADMIN`+).
- `POST /documents/{document_id}/chunk-and-embed?org_id={org_id}`: Chunk and embed a single document (Requires `ADMIN`+).
- `POST /search?org_id={org_id}`: Execute cosine similarity semantic search with query vector ranking (Requires `VIEWER`+).
- `GET /websites/{website_id}/chunks?org_id={org_id}`: List all vector chunks for a website (Requires `VIEWER`+).
- `GET /stats?org_id={org_id}`: Get vector database totals and indexing stats (Requires `VIEWER`+).

## AI Chatbot & RAG Conversations (`/api/v1/chat`)
- `POST /sessions`: Initialize a visitor chat session (generates `session_token`).
- `POST /message`: Send visitor message, run RAG retrieval + Local LLM + Tool selection, and return AI response.
- `GET /sessions/{session_id}/messages`: Retrieve full conversation history.
- `POST /test-rag?org_id={org_id}`: Authenticated dashboard test tool showing RAG debug trace, retrieved chunks, and system prompt.

## Live Visitor Conversations & Agent Inbox (`/api/v1/conversations`)
- `GET /?org_id={org_id}&website_id=...&status=...&search=...`: Paginated list of visitor conversations with latest message preview and status filter (Requires `VIEWER`+).
- `GET /{session_id}?org_id={org_id}`: Retrieve full conversation transcript and visitor session details (Requires `VIEWER`+).
- `PUT /{session_id}/status?org_id={org_id}`: Update conversation status (`BOT_ACTIVE`, `HUMAN_TAKEOVER`, `CLOSED`) (Requires `AGENT`+).
- `POST /{session_id}/agent-reply?org_id={org_id}`: Send a human agent message directly into the visitor chat thread (Requires `AGENT`+).
- `PUT /{session_id}/assign?org_id={org_id}`: Assign conversation to a team member (Requires `AGENT`+).

## E-Commerce Integrations & WooCommerce (`/api/v1/integrations`)
- `POST /woocommerce/connect?org_id={org_id}`: Connect or update WooCommerce REST API credentials for a website (Requires `ADMIN`+).
- `GET /woocommerce/{website_id}?org_id={org_id}`: Get current WooCommerce integration status and masked keys for a website (Requires `VIEWER`+).
- `POST /woocommerce/{website_id}/test?org_id={org_id}`: Test live WooCommerce connection and retrieve sample products (Requires `ADMIN`+).
- `DELETE /woocommerce/{website_id}?org_id={org_id}`: Disconnect WooCommerce integration from website (Requires `ADMIN`+).

## WhatsApp Human Handoff Bridge
- `POST /websites/{website_id}/whatsapp-preview?org_id={org_id}`: Generate live WhatsApp click-to-chat deep link and message preview with variable interpolation (Requires `VIEWER`+).

## WordPress & WooCommerce Integration Plugin
- `GET /websites/{website_id}/download-plugin?org_id={org_id}`: Dynamically generate and download pre-configured WordPress & WooCommerce plugin `.zip` archive (Requires `VIEWER`+).

## Multi-Tenant Quotas & Billing (`/api/v1/billing`)
- `GET /tiers`: Retrieve all plan tiers, pricing, and quota limits (Public).
- `GET /usage?org_id={org_id}`: Retrieve real-time usage metrics and progress percentages (Requires `VIEWER`+).
- `GET /subscription?org_id={org_id}`: Retrieve active subscription details and period renewal (Requires `VIEWER`+).
- `POST /change-tier?org_id={org_id}`: Upgrade or change subscription plan tier (Requires `ADMIN`+).

## Platform Security & Audit Trail (`/api/v1/security`)
- `GET /audit-logs?org_id={org_id}&page=1&limit=50&action=...&search=...`: Retrieve paginated security and activity audit logs (Requires `ADMIN`+).
- `POST /test-guardrails?org_id={org_id}`: Interactive security playground to scan prompt injections and redact PII (Requires `VIEWER`+).

## Conversation Analytics & Conversion Insights (`/api/v1/analytics`)
- `GET /overview?org_id={org_id}&website_id=...&period=7d|30d|90d`: High-level conversation volume, containment rate, and conversion KPIs (Requires `VIEWER`+).
- `GET /timeseries?org_id={org_id}&website_id=...&period=7d|30d|90d`: Daily conversation and message volume time-series (Requires `VIEWER`+).
- `GET /intents?org_id={org_id}&website_id=...&period=7d|30d|90d`: Topic and intent frequency distribution (Requires `VIEWER`+).
- `GET /conversions?org_id={org_id}&website_id=...&period=7d|30d|90d`: Step-by-step commerce conversion funnel data (Requires `VIEWER`+).
