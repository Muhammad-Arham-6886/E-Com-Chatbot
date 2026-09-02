# Platform Detection Architecture

## Overview
The **AI Customer & Commerce Assistant** automatically analyzes target website URLs to identify the underlying CMS and e-commerce engine:
- **WordPress**
- **WooCommerce**
- **Shopify**
- **Custom / Next.js / Other**

## Detection Heuristics
The platform uses non-blocking HTTP probes and signature inspections:

1. **WordPress**:
   - Asset markers: `wp-content/`, `wp-includes/` in HTML body.
   - Meta tags: `<meta name="generator" content="WordPress...">`.
   - Headers: `X-Powered-By: WordPress`.
   - API discovery: Probing `/wp-json/` namespace.

2. **WooCommerce**:
   - Scripts and classes: `wc-ajax`, `woocommerce`, `wc_cart_fragments`.
   - API endpoints: `/wp-json/wc/v3/` or `/wp-json/wc/v2/`.

3. **Shopify**:
   - Assets & Scripts: `cdn.shopify.com`, `shopify.theme`, `myshopify.com`.
   - Headers: `X-ShopId`, `X-Shopify-Stage`.

4. **Custom**:
   - Standard HTML fallback with 50% baseline confidence score.
