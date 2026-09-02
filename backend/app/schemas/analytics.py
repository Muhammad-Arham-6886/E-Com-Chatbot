from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class AnalyticsOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: str
    total_conversations: int
    total_messages: int
    user_messages: int
    bot_messages: int
    avg_messages_per_conversation: float
    bot_containment_rate: float
    human_escalation_rate: float
    add_to_cart_conversions: int
    product_recommendations_served: int
    whatsapp_handoffs_triggered: int


class AnalyticsTimeseriesPoint(BaseModel):
    date: str
    label: str
    conversations: int
    messages: int
    conversions: int


class AnalyticsTimeseriesResponse(BaseModel):
    points: List[AnalyticsTimeseriesPoint]


class IntentDistributionItem(BaseModel):
    intent: str
    count: int
    percentage: float


class IntentAnalyticsResponse(BaseModel):
    intents: List[IntentDistributionItem]


class FunnelStageItem(BaseModel):
    stage: str
    count: int
    conversion_rate: float


class ConversionFunnelResponse(BaseModel):
    period: str
    stages: List[FunnelStageItem]
