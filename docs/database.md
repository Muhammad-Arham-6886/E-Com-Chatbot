# Database Architecture - AI Customer & Commerce Assistant

## Database Engine
- **Primary Database**: PostgreSQL 16
- **Vector Extensions**: `pgvector`
- **ORM & Migrations**: SQLAlchemy 2.0 (Declarative with Mapped columns) + Alembic

## Core Entity Relationships

```mermaid
erDiagram
    users ||--o{ organization_members : has
    organizations ||--o{ organization_members : contains
    organizations ||--o{ audit_logs : logs
    organizations ||--o{ websites : owns
    websites ||--|| website_settings : configures
    websites ||--o{ website_domains : maps
    websites ||--o{ crawl_jobs : triggers
    websites ||--o{ knowledge_documents : stores
    websites ||--o{ chat_sessions : hosts
    websites ||--|| commerce_integrations : integrates
    crawl_jobs ||--o{ crawl_pages : discovers
    knowledge_documents ||--o{ document_chunks : chunks
    chat_sessions ||--o{ chat_messages : contains

    users {
        uuid id PK
        string email UK
        string hashed_password
        string full_name
        boolean is_active
        boolean is_verified
        timestamp created_at
        timestamp updated_at
    }

    organizations {
        uuid id PK
        string name
        string slug UK
        timestamp created_at
        timestamp updated_at
    }

    organization_members {
        uuid id PK
        uuid organization_id FK
        uuid user_id FK
        string role "OWNER | ADMIN | MANAGER | AGENT | VIEWER"
        string status "ACTIVE | INVITED | SUSPENDED"
        timestamp created_at
        timestamp updated_at
    }

    websites {
        uuid id PK
        uuid organization_id FK
        string name
        string url
        string domain
        string public_site_id UK
        string platform "WORDPRESS | WOOCOMMERCE | SHOPIFY | CUSTOM | UNKNOWN"
        string status "ACTIVE | INACTIVE | PENDING_VERIFICATION"
        timestamp created_at
        timestamp updated_at
    }

    website_settings {
        uuid id PK
        uuid website_id FK,UK
        string chatbot_name
        text welcome_message
        string placeholder_text
        string primary_color
        string secondary_color
        string launcher_position
        string widget_size
        string border_radius
        boolean enable_whatsapp
        string whatsapp_number
        text custom_instructions
        timestamp created_at
        timestamp updated_at
    }

    website_domains {
        uuid id PK
        uuid website_id FK
        string domain
        boolean is_primary
        boolean is_verified
        timestamp created_at
        timestamp updated_at
    crawl_jobs {
        uuid id PK
        uuid website_id FK
        uuid organization_id FK
        string status "PENDING | RUNNING | COMPLETED | FAILED | CANCELLED"
        integer total_pages_discovered
        integer total_pages_crawled
        integer total_pages_failed
        integer max_pages
        text error_message
        timestamp started_at
        timestamp completed_at
        timestamp created_at
        timestamp updated_at
    }

    crawl_pages {
        uuid id PK
        uuid crawl_job_id FK
        uuid website_id FK
        string url
        string status "DISCOVERED | CRAWLED | SKIPPED_ROBOTS | FAILED | DUPLICATE"
        integer status_code
        string page_title
        string content_hash
        text error
        string discovered_via
        integer depth
        timestamp created_at
        timestamp updated_at
    }

    knowledge_documents {
        uuid id PK
        uuid website_id FK
        uuid organization_id FK
        uuid crawl_page_id FK
        string url
        string title
        text meta_description
        text raw_content
        string content_hash
        integer token_count
        string status "RAW | PROCESSED | SYNCED"
        timestamp created_at
        timestamp updated_at
    }

    document_chunks {
        uuid id PK
        uuid document_id FK
        uuid website_id FK
        uuid organization_id FK
        integer chunk_index
        text content
        integer token_count
        vector embedding "vector(768) - pgvector"
        text metadata_json
        timestamp created_at
        timestamp updated_at
    }

    chat_sessions {
        uuid id PK
        uuid website_id FK
        uuid organization_id FK
        string visitor_id
        string session_token UK
        string channel "WEB_WIDGET | DASHBOARD_TEST"
        text metadata_json
        timestamp created_at
        timestamp updated_at
    }

    chat_messages {
        uuid id PK
        uuid session_id FK
        string sender "USER | BOT | AGENT | SYSTEM"
        text content
        text sources_json
        text suggested_actions_json
        text tool_call_json
        integer token_count
        timestamp created_at
        timestamp updated_at
    }

    commerce_integrations {
        uuid id PK
        uuid website_id FK UK
        uuid organization_id FK
        string platform "WOOCOMMERCE | SHOPIFY | CUSTOM"
        string api_url
        string consumer_key
        string consumer_secret
        boolean is_active
        timestamp last_sync_at
        text metadata_json
        timestamp created_at
        timestamp updated_at
    }

    organization_subscriptions {
        uuid id PK
        uuid organization_id FK UK
        string tier "FREE | STARTER | GROWTH | ENTERPRISE"
        string status "ACTIVE | TRIALING | PAST_DUE | CANCELLED"
        timestamp current_period_start
        timestamp current_period_end
        boolean cancel_at_period_end
        timestamp created_at
        timestamp updated_at
    }

    organization_usage {
        uuid id PK
        uuid organization_id FK
        string billing_period "2026-08"
        integer chat_messages_count
        integer crawl_pages_count
        integer vector_chunks_count
        integer tokens_consumed
        timestamp last_reset_at
        timestamp created_at
        timestamp updated_at
    }
```

## Indexing Strategy
- `users`: B-Tree index on `email` (Unique).
- `organizations`: B-Tree index on `slug` (Unique).
- `organization_members`: Composite Unique index on `(organization_id, user_id)` and B-Tree on `user_id`.
- `websites`: B-Tree on `organization_id`, `domain`, and Unique B-Tree on `public_site_id`.
- `website_settings`: Unique B-Tree on `website_id`.
- `website_domains`: B-Tree on `website_id` and `domain`.
- `crawl_jobs`: B-Tree on `website_id`, `organization_id`, `status`.
- `crawl_pages`: B-Tree on `crawl_job_id`, `website_id`, `url`, `content_hash`.
- `knowledge_documents`: B-Tree on `website_id`, `organization_id`, `url`, `content_hash`.
- `document_chunks`: B-Tree on `document_id`, `website_id`, `organization_id`, and HNSW Cosine Index on `embedding (vector_cosine_ops)`.
- `chat_sessions`: B-Tree on `website_id`, `organization_id`, `visitor_id`, `status`, `last_message_at`, and Unique B-Tree on `session_token`.
- `chat_messages`: B-Tree on `session_id`, `created_at`.
- `commerce_integrations`: B-Tree on `organization_id` and Unique B-Tree on `website_id`.
- `organization_subscriptions`: B-Tree on `id` and Unique B-Tree on `organization_id`.
- `organization_usage`: B-Tree on `organization_id`, `billing_period`, and Unique Composite on `(organization_id, billing_period)`.
