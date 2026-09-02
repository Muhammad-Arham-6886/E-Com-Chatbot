# System Architecture - AI Customer & Commerce Assistant SaaS

## Overview
The **AI Customer & Commerce Assistant** is a multi-tenant, production-ready SaaS platform enabling businesses to index their websites, build automated knowledge bases, and provide intelligent customer service and commerce assistance via embeddable chat widgets.

## High-Level Architecture Diagram

```
+---------------------------------------------------------------------------------------+
|                                    Client Tier                                        |
|  +---------------------------+  +---------------------------+  +-------------------+  |
|  | Next.js Admin Dashboard   |  | Embeddable JS Chat Widget |  | 3rd Party Website |  |
|  +-------------+-------------+  +-------------+-------------+  +---------+---------+  |
+----------------|------------------------------|--------------------------|------------+
                 |                              |                          |
                 +-----------------------+      |                          |
                                         v      v                          |
+--------------------------------------------------------------------------v------------+
|                                   Application Gateway                                 |
|                             FastAPI (Async REST API & WebSockets)                     |
|  - Rate Limiting   - JWT/Session Auth   - CORS / Security Headers   - Tenant Context  |
+----------------------------------------+----------------------------------------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
+------------------+           +-------------------+           +-------------------+
|  Auth & Org Svc  |           |  Knowledge & RAG  |           |  Commerce Engine  |
|  - RBAC & Teams  |           |  - PgVector Embed |           |  - WooCommerce    |
|  - Multi-Tenancy |           |  - Ollama Engine  |           |  - Shopify        |
+--------+---------+           +---------+---------+           +---------+---------+
         |                               |                               |
         v                               v                               v
+------------------+           +-------------------+           +-------------------+
| PostgreSQL 16    |           | Celery Workers    |           | Local AI Server   |
| - Relational DB  |           | - Web Crawler     |           | - Ollama (LLM)    |
| - pgvector ext   |           | - Async Embedder  |           | - Local Embeddings|
+------------------+           | - Sync Pipelines  |           +-------------------+
                               +---------+---------+
                                         |
                                         v
                               +-------------------+
                               | Redis 7 Cache &   |
                               | Task Broker       |
                               +-------------------+
```

## Core Architectural Principles
1. **Clean Architecture & Separation of Concerns**:
   - `app/api`: HTTP Routing, Request validation (Pydantic), Response serialization.
   - `app/services`: Business logic, domain rules, orchestration.
   - `app/models`: SQLAlchemy persistence entities with strict foreign key constraints.
   - `app/schemas`: Strongly-typed input and output DTOs.
   - `app/core`: Configuration, Security, DB session lifecycle, Celery setup.

2. **Multi-Tenancy From Day One**:
   - Hierarchy: `User` -> `Organization` -> `Websites`.
   - Every tenant-owned database record contains `organization_id` (and `website_id` where applicable).
   - Strict backend dependency injection verifies tenant membership and roles before allowing read/write operations.

3. **Provider-Agnostic AI & Commerce**:
   - AI interfaces (`AIProvider`, `EmbeddingProvider`) allow seamless swapping between local Ollama and future cloud LLMs (OpenAI, Gemini, Anthropic).
   - Commerce interfaces (`CommerceProvider`) decouple core conversation flows from specific platforms (WooCommerce, Shopify).
