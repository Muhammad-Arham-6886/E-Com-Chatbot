# WordPress & WooCommerce Integration Plugin Guide (Phase 10)

The **Official WordPress & WooCommerce Integration Plugin** (`ai-commerce-assistant`) provides a turnkey, zero-code solution for embedding the AI Customer & Commerce Assistant on WordPress websites and WooCommerce storefronts.

---

## 1. Zero-Configuration Dynamic ZIP Architecture

When downloaded from the SaaS Dashboard:
1. The SaaS backend dynamically packages `ai-commerce-assistant.zip` in memory.
2. It automatically writes the website's `public_site_id` and SaaS API URL into the plugin's default activation options.
3. When the WordPress site administrator uploads and activates the `.zip` file, the chatbot immediately appears on their storefront without requiring manual copy-pasting of API keys or script editing!

```
[ SaaS Dashboard ] ──▶ GET /api/v1/websites/{id}/download-plugin
                             │
                             ▼
              [ Dynamic In-Memory ZIP Packager ]
                             │
      (Injects public_site_id & SaaS API URL into plugin)
                             │
                             ▼
              [ Download ai-commerce-assistant.zip ]
                             │
                             ▼
       [ Upload to WordPress Admin -> Plugins -> Add New ]
                             │
                             ▼
              [ Click "Activate Plugin" ]
                             │
                             ▼
   [ AI Chatbot Instantly Live on Storefront wp_footer ]
```

---

## 2. Plugin Structure

```text
wordpress-plugin/ai-commerce-assistant/
├── ai-commerce-assistant.php        # Main plugin entry point & singleton initialization
├── includes/
│   ├── class-settings.php           # Admin settings menu (Settings -> AI Assistant)
│   ├── class-widget-embed.php       # Injects widget.js into wp_footer automatically
│   └── class-woocommerce.php        # WooCommerce hooks, custom redirects, and notices
└── readme.txt                       # Standard WordPress repository documentation
```

---

## 3. WordPress Admin Features

- **Settings Menu**: Accessible via **Settings ➔ AI Assistant** or **WooCommerce ➔ AI Assistant**.
- **Options**:
  - `Public Site ID`: Pre-filled automatically.
  - `SaaS Platform API URL`: Pre-filled automatically.
  - `Enable Chat Widget`: On/Off toggle.
  - `Hide for Admin Users`: Optional toggle to avoid test clutter during administrative browsing.
  - `WooCommerce REST API Setup Guide`: Step-by-step instructions for generating read/write keys for live catalog integration.

---

## 4. REST API Endpoint

| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/websites/{website_id}/download-plugin?org_id={id}` | Dynamically generates and downloads the pre-configured plugin `.zip` archive | `VIEWER`+ |
