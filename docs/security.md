# Security Architecture

## 1. Password Security
- Passwords are encrypted using salted `bcrypt` algorithms.
- Plaintext passwords are never logged, serialized, or returned in API responses.

## 2. Multi-Tenant Authorization Enforcement
- Every database query for tenant-scoped resources uses explicit filtering by `organization_id`.
- The FastAPI dependency `require_org_member(role)` validates ownership and membership before the request enters business service logic.

## 3. Input Validation & Parameterized Queries
- Pydantic models validate and sanitize all payload structures.
- SQLAlchemy 2.0 uses parameterized query execution, preventing SQL injection vulnerabilities.

## 4. CORS & Headers
- Restrictive CORS origins specified via `CORS_ORIGINS` environment variables.
- Standard secure HTTP headers.

## 5. SSRF (Server-Side Request Forgery) Protection & Crawler Sandbox
- **Mandatory Pre-Flight Validation**: Outbound crawler requests resolve hostnames to IP addresses before initiating connections (`SSRFGuard.validate_url`).
- **Forbidden Ranges**:
  - Loopback (`127.0.0.0/8`, `::1`)
  - RFC 1918 Private Subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`)
  - Link-Local & Cloud Metadata (`169.254.0.0/16`, `169.254.169.254`, `metadata.google.internal`)
  - IPv6 Unique Local & Link-Local (`fc00::/7`, `fe80::/10`)
  - Broadcast & Multicast (`224.0.0.0/4`, `255.255.255.255/32`, `ff00::/8`)
- **Strict Domain Locking**: The crawler strictly confines page traversal to the target domain, rejecting redirection or links pointing to external or arbitrary hosts.
- **Resource Limits**: Configurable timeouts (10s max), crawl depth boundaries, and `max_pages` bounds (1 to 1000) prevent infinite crawl loops and denial-of-service.
