# Conversation Analytics & Conversion Insights Guide (Phase 13)

The **Conversation Analytics & Conversion Insights Engine** provides real-time visibility into customer inquiries, bot autonomous resolution rates, commerce conversion metrics, and time-series engagement trends.

---

## 1. Key Metrics & Calculations

### Core Support Metrics
- **Total Conversations**: Count of visitor chat sessions created within the selected time window.
- **Total Messages**: Count of messages exchanged (User, Bot, Human Agent).
- **Average Session Depth**: Average number of messages exchanged per visitor session.
- **Bot Containment Rate**: Percentage of conversations resolved autonomously by AI without requiring human agent takeover or WhatsApp escalation:
  $$\text{Containment Rate} = \frac{\text{Autonomous Sessions}}{\text{Total Sessions}} \times 100$$
- **Human Escalation Rate**: Percentage of conversations escalated to WhatsApp or a human support agent:
  $$\text{Escalation Rate} = 100 - \text{Containment Rate}$$

### Commerce & Conversion Metrics
- **Add-to-Cart Conversions**: Direct add-to-cart clicks generated via AI product cards or cart action buttons.
- **Product Recommendations Served**: Frequency of AI tool calls querying catalog products (`search_products`, `get_product_details`).
- **WhatsApp Handoffs**: Direct click-to-chat triggers pre-filling visitor inquiry context into WhatsApp.

---

## 2. Conversion Funnel Stages

```
[ Stage 1: Chat Sessions Started ]
              │
              ▼
[ Stage 2: Product Recommendations Viewed ]
              │
              ▼
[ Stage 3: Add to Cart Actions ]
              │
              ▼
[ Stage 4: Human / WhatsApp Handoffs ]
```

---

## 3. REST API Reference (`/api/v1/analytics`)

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/analytics/overview?org_id={id}&website_id=...&period=7d\|30d\|90d` | Retrieve high-level summary KPIs and conversion totals | `VIEWER`+ |
| `GET` | `/api/v1/analytics/timeseries?org_id={id}&website_id=...&period=7d\|30d\|90d` | Retrieve daily conversation volume time-series data | `VIEWER`+ |
| `GET` | `/api/v1/analytics/intents?org_id={id}&website_id=...&period=7d\|30d\|90d` | Retrieve inquiry intent distribution and topic percentages | `VIEWER`+ |
| `GET` | `/api/v1/analytics/conversions?org_id={id}&website_id=...&period=7d\|30d\|90d` | Retrieve step-by-step commerce conversion funnel data | `VIEWER`+ |
