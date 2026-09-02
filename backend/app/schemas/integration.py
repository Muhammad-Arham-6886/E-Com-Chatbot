from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ProductCardResponse(BaseModel):
    id: str
    name: str
    price: float
    currency: str = "USD"
    description: str = ""
    image_url: Optional[str] = None
    product_url: str = "#"
    in_stock: bool = True


class WooCommerceConnectRequest(BaseModel):
    website_id: str = Field(..., description="Target website UUID")
    api_url: str = Field(..., description="Store URL e.g. https://mystore.com")
    consumer_key: str = Field(..., min_length=5, description="WooCommerce Consumer Key (ck_...)")
    consumer_secret: str = Field(..., min_length=5, description="WooCommerce Consumer Secret (cs_...)")
    is_active: bool = True


class WooCommerceIntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    website_id: str
    organization_id: str
    platform: str
    api_url: str
    consumer_key_masked: str
    is_active: bool
    last_sync_at: Optional[datetime] = None
    metadata_json: Optional[str] = None
    created_at: datetime


class WooCommerceTestResponse(BaseModel):
    success: bool
    status_code: int
    message: str
    currency: str = "USD"
    product_count: int = 0
    sample_products: List[ProductCardResponse] = Field(default_factory=list)
