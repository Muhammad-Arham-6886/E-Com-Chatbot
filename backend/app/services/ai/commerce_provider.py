import html
import re
from typing import List, Optional
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


class ProductCard:
    def __init__(
        self,
        id: str,
        name: str,
        price: float,
        currency: str = "USD",
        description: str = "",
        image_url: Optional[str] = None,
        product_url: str = "#",
        in_stock: bool = True,
    ):
        self.id = str(id)
        self.name = name
        self.price = price
        self.currency = currency
        self.description = description
        self.image_url = image_url
        self.product_url = product_url
        self.in_stock = in_stock

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "currency": self.currency,
            "description": self.description,
            "image_url": self.image_url,
            "product_url": self.product_url,
            "in_stock": self.in_stock,
        }


class CommerceProvider:
    @property
    def is_mock(self) -> bool:
        return False

    async def test_connection(self) -> dict:
        raise NotImplementedError

    async def search_products(self, query: str, limit: int = 4) -> List[ProductCard]:
        raise NotImplementedError

    async def get_product(self, product_id: str) -> Optional[ProductCard]:
        raise NotImplementedError

    async def get_add_to_cart_url(self, product_id: str, quantity: int = 1) -> str:
        raise NotImplementedError


class MockCommerceProvider(CommerceProvider):
    """Used when no real WooCommerce store is connected. Returns empty results."""

    @property
    def is_mock(self) -> bool:
        return True

    def __init__(self, base_url: str = "https://store.local"):
        self.base_url = base_url.rstrip("/")

    async def test_connection(self) -> dict:
        return {
            "success": False,
            "status_code": 0,
            "message": "No store connected. Connect your WooCommerce store in Integrations.",
            "currency": "USD",
            "product_count": 0,
        }

    async def search_products(self, query: str, limit: int = 4) -> List[ProductCard]:
        return []

    async def get_product(self, product_id: str) -> Optional[ProductCard]:
        return None

    async def get_add_to_cart_url(self, product_id: str, quantity: int = 1) -> str:
        return f"{self.base_url}/cart?add-to-cart={product_id}&quantity={quantity}"


class WooCommerceProvider(CommerceProvider):
    def __init__(
        self,
        api_url: str,
        consumer_key: str,
        consumer_secret: str,
        custom_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.consumer_key = consumer_key.strip()
        self.consumer_secret = consumer_secret.strip()
        self.custom_client = custom_client
        self._is_mock = (
            self.consumer_key.startswith("ck_test")
            or "localhost" in self.api_url
            or "store.local" in self.api_url
        )

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    @staticmethod
    def _strip_html(text: str) -> str:
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", text)
        return html.unescape(clean).strip()

    def _get_auth(self):
        return (self.consumer_key, self.consumer_secret)

    async def test_connection(self) -> dict:
        if self._is_mock:
            return {
                "success": False,
                "status_code": 0,
                "message": "Test/mock credentials. Connect real WooCommerce API keys.",
                "currency": "USD",
                "product_count": 0,
            }

        client = self.custom_client or httpx.AsyncClient(timeout=10.0)
        should_close = self.custom_client is None
        try:
            url = f"{self.api_url}/wp-json/wc/v3/products"
            resp = await client.get(url, auth=self._get_auth(), params={"per_page": 1})
            if resp.status_code == 200:
                total_products = int(resp.headers.get("X-WP-Total", 1))
                return {
                    "success": True,
                    "status_code": 200,
                    "message": "WooCommerce REST API connected successfully.",
                    "currency": "USD",
                    "product_count": total_products,
                }
            return {
                "success": False,
                "status_code": resp.status_code,
                "message": f"WooCommerce returned HTTP {resp.status_code}: {resp.text[:150]}",
                "currency": "USD",
                "product_count": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 500,
                "message": f"Failed to connect to WooCommerce: {str(e)}",
                "currency": "USD",
                "product_count": 0,
            }
        finally:
            if should_close:
                await client.aclose()

    async def search_products(self, query: str, limit: int = 4) -> List[ProductCard]:
        if self._is_mock:
            return []

        client = self.custom_client or httpx.AsyncClient(timeout=10.0)
        should_close = self.custom_client is None
        try:
            url = f"{self.api_url}/wp-json/wc/v3/products"
            params = {
                "search": query,
                "per_page": limit,
                "status": "publish",
            }
            resp = await client.get(url, auth=self._get_auth(), params=params)
            if resp.status_code == 200:
                items = resp.json()
                products = []
                for item in items:
                    images = item.get("images", [])
                    img_url = images[0].get("src") if images else None
                    raw_price = item.get("price") or item.get("regular_price") or item.get("sale_price") or "0"
                    try:
                        price_val = float(raw_price)
                    except (ValueError, TypeError):
                        price_val = 0.0
                    products.append(
                        ProductCard(
                            id=str(item.get("id")),
                            name=item.get("name", "Product"),
                            price=price_val,
                            currency=item.get("currency", "USD"),
                            description=self._strip_html(item.get("short_description") or item.get("description") or ""),
                            image_url=img_url,
                            product_url=item.get("permalink", f"{self.api_url}/product/{item.get('slug')}"),
                            in_stock=(item.get("stock_status") != "outofstock"),
                        )
                    )
                return products
        except Exception:
            pass
        finally:
            if should_close:
                await client.aclose()

        return []

    async def get_product(self, product_id: str) -> Optional[ProductCard]:
        if self._is_mock:
            return None

        client = self.custom_client or httpx.AsyncClient(timeout=10.0)
        should_close = self.custom_client is None
        try:
            url = f"{self.api_url}/wp-json/wc/v3/products/{product_id}"
            resp = await client.get(url, auth=self._get_auth())
            if resp.status_code == 200:
                item = resp.json()
                images = item.get("images", [])
                img_url = images[0].get("src") if images else None
                raw_price = item.get("price") or item.get("regular_price") or item.get("sale_price") or "0"
                try:
                    price_val = float(raw_price)
                except (ValueError, TypeError):
                    price_val = 0.0
                return ProductCard(
                    id=str(item.get("id")),
                    name=item.get("name", "Product"),
                    price=price_val,
                    currency=item.get("currency", "USD"),
                    description=self._strip_html(item.get("short_description") or item.get("description") or ""),
                    image_url=img_url,
                    product_url=item.get("permalink", f"{self.api_url}/product/{item.get('slug')}"),
                    in_stock=(item.get("stock_status") != "outofstock"),
                )
        except Exception:
            pass
        finally:
            if should_close:
                await client.aclose()

        return None

    async def get_add_to_cart_url(self, product_id: str, quantity: int = 1) -> str:
        return f"{self.api_url}/cart/?add-to-cart={product_id}&quantity={quantity}"


async def get_commerce_provider_for_website(
    db: AsyncSession,
    website_id: str,
) -> CommerceProvider:
    from app.models.integration import CommerceIntegration

    stmt = select(CommerceIntegration).where(
        and_(
            CommerceIntegration.website_id == website_id,
            CommerceIntegration.is_active == True,
        )
    )
    integration = (await db.execute(stmt)).scalar_one_or_none()
    if integration and integration.platform == "WOOCOMMERCE":
        return WooCommerceProvider(
            api_url=integration.api_url,
            consumer_key=integration.consumer_key,
            consumer_secret=integration.consumer_secret,
        )

    return MockCommerceProvider()
