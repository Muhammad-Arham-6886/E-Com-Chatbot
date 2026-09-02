from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class UsageMetricItem(BaseModel):
    used: int
    limit: int
    percentage: float


class UsageBreakdownResponse(BaseModel):
    tier: str
    tier_name: str
    price_monthly: int
    status: str
    billing_period: str
    period_end: Optional[datetime] = None
    websites: UsageMetricItem
    chat_messages: UsageMetricItem
    vector_chunks: UsageMetricItem
    tokens_consumed: int


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    tier: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False


class PlanTierInfo(BaseModel):
    tier: str
    name: str
    price_monthly: int
    max_websites: int
    max_pages_per_crawl: int
    max_chunks: int
    max_monthly_messages: int
    rate_limit_rpm: int
    features: List[str]


class ChangeTierRequest(BaseModel):
    tier: str = Field(..., description="Target tier: FREE, STARTER, GROWTH, ENTERPRISE")
