import re
from typing import List, Tuple, Optional
from urllib.parse import urlparse
import httpx
from app.models.enums import PlatformEnum


class PlatformDetector:
    @staticmethod
    def normalize_url(raw_url: str) -> Tuple[str, str]:
        """
        Validates and normalizes raw URL.
        Returns:
            (normalized_url, domain)
            e.g. ('https://example.com', 'example.com')
        """
        url = raw_url.strip()
        if not url:
            raise ValueError("URL cannot be empty.")

        # Ensure scheme is present
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("Invalid URL format.")

        # Extract hostname and clean domain
        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]

        # Strip www. prefix for canonical domain comparison if desired, but keep hostname intact
        canonical_domain = re.sub(r"^www\.", "", domain)

        # Base normalized URL (scheme + netloc)
        scheme = parsed.scheme.lower()
        normalized_url = f"{scheme}://{parsed.netloc}"

        return normalized_url, canonical_domain

    @staticmethod
    async def detect_platform(
        url: str, custom_client: Optional[httpx.AsyncClient] = None
    ) -> Tuple[PlatformEnum, float, List[str]]:
        """
        Runs non-blocking platform detection heuristics against a public URL.
        Returns:
            (detected_platform, confidence_score, signals)
        """
        signals: List[str] = []
        platform = PlatformEnum.UNKNOWN
        confidence = 0.0

        try:
            client = custom_client or httpx.AsyncClient(
                timeout=5.0,
                follow_redirects=True,
                headers={"User-Agent": "AI-Commerce-Assistant-Detector/1.0"},
            )
            should_close = custom_client is None

            try:
                # 1. Fetch homepage
                resp = await client.get(url)
                body = resp.text.lower()
                headers = {k.lower(): v.lower() for k, v in resp.headers.items()}

                # Check WordPress / WooCommerce signals
                wp_signals = 0
                if "wp-content" in body or "wp-includes" in body:
                    signals.append("WordPress asset path discovered")
                    wp_signals += 1
                if '<meta name="generator" content="wordpress' in body:
                    signals.append("WordPress generator meta tag present")
                    wp_signals += 2
                if "x-powered-by" in headers and "wordpress" in headers["x-powered-by"]:
                    signals.append("WordPress X-Powered-By header found")
                    wp_signals += 2

                # Check WooCommerce specific signals
                woo_signals = 0
                if "woocommerce" in body or "wc-ajax" in body or "wc_cart_fragments" in body:
                    signals.append("WooCommerce script or class markers found")
                    woo_signals += 2

                # Check Shopify signals
                shopify_signals = 0
                if "cdn.shopify.com" in body or "shopify.theme" in body or "myshopify.com" in body:
                    signals.append("Shopify CDN or theme javascript detected")
                    shopify_signals += 2
                if "x-shopid" in headers or "x-shopify-stage" in headers:
                    signals.append("Shopify HTTP response headers present")
                    shopify_signals += 3

                # Evaluate detections
                if shopify_signals >= 2:
                    platform = PlatformEnum.SHOPIFY
                    confidence = 0.95 if shopify_signals >= 3 else 0.80
                elif woo_signals >= 2:
                    platform = PlatformEnum.WOOCOMMERCE
                    confidence = 0.90
                elif wp_signals >= 1:
                    # Probe /wp-json/ as additional verification
                    try:
                        wp_json_resp = await client.get(f"{url.rstrip('/')}/wp-json/")
                        if wp_json_resp.status_code == 200:
                            signals.append("WordPress REST API /wp-json/ endpoint active")
                            wp_signals += 1
                            if "wc/v" in wp_json_resp.text.lower():
                                signals.append("WooCommerce REST namespace discovered")
                                platform = PlatformEnum.WOOCOMMERCE
                                confidence = 0.98
                                return platform, confidence, signals
                    except Exception:
                        pass

                    platform = PlatformEnum.WORDPRESS
                    confidence = 0.90 if wp_signals >= 2 else 0.70
                else:
                    platform = PlatformEnum.CUSTOM
                    confidence = 0.50
                    signals.append("Standard website markup detected (Custom / Other)")

            finally:
                if should_close:
                    await client.aclose()

        except Exception as e:
            platform = PlatformEnum.UNKNOWN
            confidence = 0.0
            signals.append(f"Network probe failed or host unreachable: {str(e)}")

        return platform, confidence, signals
