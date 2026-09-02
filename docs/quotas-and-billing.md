# Multi-Tenant Quotas, Rate Limiting & Billing Guide (Phase 11)

The **Multi-Tenant Quotas, Usage Metering & Billing System** enforces tiered resource constraints, tracks monthly AI message utilization, monitors vector indexing allowances, and provides self-service plan upgrades across all organizations.

---

## 1. Subscription Tier Matrix

| Feature / Limit | Free Sandbox | Starter Pro | Growth Business | Enterprise Scale |
| :--- | :--- | :--- | :--- | :--- |
| **Monthly Price** | **$0 / mo** | **$29 / mo** | **$79 / mo** | **$299 / mo** |
| **Connected Websites** | 1 Website | 3 Websites | 10 Websites | Unlimited (∞) |
| **Max Pages / Crawl** | 50 Pages | 500 Pages | 2,500 Pages | Unlimited (∞) |
| **Vector Chunks** | 100 Chunks | 2,000 Chunks | 10,000 Chunks | Unlimited (∞) |
| **Monthly AI Messages** | 200 Messages | 2,000 Messages | 10,000 Messages | Unlimited (∞) |
| **Rate Limit** | 60 req/min | 120 req/min | 300 req/min | 1,000 req/min |
| **WooCommerce Integration** | Basic | Full REST v3 | Full REST v3 | Full REST v3 |
| **WhatsApp Human Bridge** | Standard | Standard | Advanced | Dedicated SLA |

---

## 2. Quota Enforcement Logic

```
[ Incoming Action (e.g., Create Website / AI Message / Crawl) ]
                               │
                               ▼
                        [ QuotaService ]
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
[ Within Plan Allowance ]               [ Limit Exceeded ]
       │                                               │
       ▼                                               ▼
Executes action & increments usage       • Management Action ➔ 402 Payment Required
                                         • Customer Chat ➔ Polite Notice & System Message
```

---

## 3. Database Schema

### `organization_subscriptions`
- `id`: UUID Primary Key
- `organization_id`: Unique Foreign Key (`organizations.id`, CASCADE)
- `tier`: `FREE` | `STARTER` | `GROWTH` | `ENTERPRISE`
- `status`: `ACTIVE` | `TRIALING` | `PAST_DUE` | `CANCELLED`
- `current_period_start`: Timestamp
- `current_period_end`: Timestamp
- `cancel_at_period_end`: Boolean

### `organization_usage`
- `id`: UUID Primary Key
- `organization_id`: Foreign Key (`organizations.id`, CASCADE)
- `billing_period`: String (`"2026-08"`)
- `chat_messages_count`: Integer
- `crawl_pages_count`: Integer
- `vector_chunks_count`: Integer
- `tokens_consumed`: Integer
- `last_reset_at`: Timestamp
- Unique Constraint: `(organization_id, billing_period)`

---

## 4. REST API Reference (`/api/v1/billing`)

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/billing/tiers` | Retrieve all plan tiers, pricing, and quota limits | Public |
| `GET` | `/api/v1/billing/usage?org_id={id}` | Retrieve real-time usage metrics and progress percentages | `VIEWER`+ |
| `GET` | `/api/v1/billing/subscription?org_id={id}` | Retrieve active subscription details and period renewal | `VIEWER`+ |
| `POST` | `/api/v1/billing/change-tier?org_id={id}` | Upgrade or change subscription plan tier | `ADMIN`+ |
