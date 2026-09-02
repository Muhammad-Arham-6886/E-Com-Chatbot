# JavaScript Chat Widget Integration Guide (Phase 6)

The **AI Customer & Commerce Assistant** embeddable widget is a zero-dependency, lightweight Vanilla JavaScript client that runs inside an isolated **Shadow DOM**.

---

## 1. Quick Installation

Add this single script tag right before the closing `</body>` tag of your website:

```html
<script 
  src="https://your-domain.com/static/widget.js" 
  data-site-id="YOUR_PUBLIC_SITE_ID"
  async 
  defer>
</script>
```

---

## 2. Architecture & Design

```
Host Webpage (WordPress, WooCommerce, Shopify, Next.js)
       │
       ▼
[ <div id="ai-commerce-widget-root"> ]
       │
       ▼ (Shadow DOM Encapsulation)
 ┌─────────────────────────────────────────────────────────────┐
 │ #shadow-root (open)                                         │
 │                                                             │
 │  • Isolated Scoped CSS (Zero style pollution)               │
 │  • Floating Launcher Button (Customizable Brand Color)      │
 │  • Animated Chat Window & Header                            │
 │  • Message Stream & Markdown Parser                         │
 │  • Product Recommendation Cards (With images, prices & CTAs)│
 │  • WhatsApp Escalation Button (Direct deep-link)            │
 │  • Verified Source Citations Pill Links                     │
 │  • Typing Wave Indicator                                    │
 └─────────────────────────────────────────────────────────────┘
```

---

## 3. Platform Specific Installation

### WordPress / WooCommerce
1. Install and activate the free **WPCode** (or "Insert Headers and Footers") plugin.
2. Navigate to **Code Snippets** ➔ **Header & Footer**.
3. Paste the script tag into the **Footer** section and click **Save Changes**.
*Alternatively, add the snippet directly before `<?php wp_footer(); ?>` in your active theme's `footer.php`.*

### Shopify
1. In your Shopify Admin, go to **Online Store** ➔ **Themes**.
2. Click **Actions (...)** ➔ **Edit code**.
3. Open `layout/theme.liquid`.
4. Paste the `<script>` tag immediately before `</body>` and click **Save**.

### Next.js (App Router / Pages Router)
```tsx
import Script from 'next/script';

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        {children}
        <Script
          src="https://your-domain.com/static/widget.js"
          data-site-id="YOUR_PUBLIC_SITE_ID"
          strategy="lazyOnload"
        />
      </body>
    </html>
  );
}
```

---

## 4. Script Attributes & Configuration

| Attribute | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `data-site-id` | **Yes** | `null` | The unique `public_site_id` generated for the website in the SaaS dashboard. |
| `data-api-url` | Optional | `http://localhost:8000` | The backend API server URL (omit if hosted on the same origin). |

---

## 5. Live Demo Store
A simulated e-commerce demo store is available at [`frontend/public/widget-demo.html`](file:///c:/Users/fattani%20computers/Documents/Chatbot/frontend/public/widget-demo.html).
