# WooCommerce REST API v3 Integration Guide (Phase 8)

The **AI Customer & Commerce Assistant** integrates directly with the official WooCommerce REST API v3 to power real-time product discovery, stock checks, and direct shopping cart checkouts.

---

## 1. How It Works

```
[ Customer asks: "Show me mechanical keyboards" ]
                         │
                         ▼
             [ Tool Selection Engine ]
                         │
           Intent: SEARCH_PRODUCT ("keyboards")
                         │
                         ▼
        [ get_commerce_provider_for_website() ]
                         │
       ┌─────────────────┴─────────────────┐
       ▼                                   ▼
 [ WooCommerceProvider ]            [ MockCommerceProvider ]
  (If API keys connected)            (If not connected)
       │
       ▼
 [ GET /wp-json/wc/v3/products?search=keyboards&status=publish ]
       │
       ▼
 [ ProductCards: Title, Price, Currency, Image, Add-To-Cart URL ]
       │
       ▼
 [ Delivered into Chat Stream + WhatsApp Escalation Option ]
```

---

## 2. Generating WooCommerce API Keys

1. In WordPress Admin, navigate to **WooCommerce** ➔ **Settings** ➔ **Advanced** ➔ **REST API**.
2. Click **Add key**.
3. Set:
   - **Description**: `AI Commerce Assistant SaaS`
   - **User**: Select an Administrator account.
   - **Permissions**: `Read` (or `Read/Write`).
4. Click **Generate API key**.
5. Copy the generated **Consumer Key** (`ck_...`) and **Consumer Secret** (`cs_...`) into the SaaS dashboard at [`/dashboard/integrations`](file:///c:/Users/fattani%20computers/Documents/Chatbot/frontend/src/app/dashboard/integrations/page.tsx).

---

## 3. Direct Add to Cart Action Links

The integration automatically generates direct cart add links for customers:
```text
https://yourstore.com/cart/?add-to-cart={product_id}&quantity={quantity}
```
When clicked inside the chatbot widget, this immediately puts the item in the customer's cart and redirects to checkout.

---

## 4. REST API Endpoints (`/api/v1/integrations/woocommerce`)

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/integrations/woocommerce/connect?org_id={id}` | Validate and store WooCommerce REST API keys for a website | `ADMIN`+ |
| `GET` | `/api/v1/integrations/woocommerce/{website_id}?org_id={id}` | Get connection status, masked keys, and last sync timestamp | `VIEWER`+ |
| `POST` | `/api/v1/integrations/woocommerce/{website_id}/test?org_id={id}` | Ping WooCommerce store and retrieve live sample products | `ADMIN`+ |
| `DELETE` | `/api/v1/integrations/woocommerce/{website_id}?org_id={id}` | Disconnect WooCommerce integration | `ADMIN`+ |
