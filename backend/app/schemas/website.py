from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from app.models.enums import PlatformEnum, WebsiteStatusEnum


class WebsiteSettingsBase(BaseModel):
    chatbot_name: str = Field(default="AI Assistant", min_length=1, max_length=255)
    welcome_message: str = Field(default="Hi there! How can I help you today?")
    placeholder_text: str = Field(default="Type your message here...", max_length=255)
    primary_color: str = Field(default="#4F46E5", max_length=32)
    secondary_color: str = Field(default="#1E1B4B", max_length=32)
    launcher_position: str = Field(default="bottom-right", max_length=32)
    widget_size: str = Field(default="medium", max_length=32)
    border_radius: str = Field(default="16px", max_length=32)
    enable_whatsapp: bool = False
    whatsapp_number: Optional[str] = Field(None, max_length=64)
    whatsapp_custom_message: Optional[str] = None
    whatsapp_handoff_trigger: str = Field(default="ON_ESCALATION", max_length=32)
    custom_instructions: Optional[str] = None


class WebsiteSettingsUpdate(BaseModel):
    chatbot_name: Optional[str] = Field(None, min_length=1, max_length=255)
    welcome_message: Optional[str] = None
    placeholder_text: Optional[str] = Field(None, max_length=255)
    primary_color: Optional[str] = Field(None, max_length=32)
    secondary_color: Optional[str] = Field(None, max_length=32)
    launcher_position: Optional[str] = Field(None, max_length=32)
    widget_size: Optional[str] = Field(None, max_length=32)
    border_radius: Optional[str] = Field(None, max_length=32)
    enable_whatsapp: Optional[bool] = None
    whatsapp_number: Optional[str] = Field(None, max_length=64)
    whatsapp_custom_message: Optional[str] = None
    whatsapp_handoff_trigger: Optional[str] = Field(None, max_length=32)
    custom_instructions: Optional[str] = None


class WebsiteSettingsResponse(WebsiteSettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    website_id: str
    created_at: datetime
    updated_at: datetime


class WebsiteDomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain: str
    is_primary: bool
    is_verified: bool
    created_at: datetime


class WebsiteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., description="Full website URL e.g. https://example.com")


class WebsiteCreate(WebsiteBase):
    pass


class WebsiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = None
    status: Optional[WebsiteStatusEnum] = None
    platform: Optional[PlatformEnum] = None


class WebsiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    url: str
    domain: str
    public_site_id: str
    platform: PlatformEnum
    status: WebsiteStatusEnum
    created_at: datetime
    updated_at: datetime


class WebsiteDetailResponse(WebsiteResponse):
    settings: Optional[WebsiteSettingsResponse] = None
    domains: List[WebsiteDomainResponse] = []


class PublicWidgetConfigResponse(BaseModel):
    website_id: str
    public_site_id: str
    website_name: str
    chatbot_name: str
    welcome_message: str
    placeholder_text: str
    primary_color: str
    secondary_color: str
    launcher_position: str
    widget_size: str
    border_radius: str
    enable_whatsapp: bool
    whatsapp_number: Optional[str] = None
    whatsapp_custom_message: Optional[str] = None
    whatsapp_handoff_trigger: str = "ON_ESCALATION"
    api_base_url: str = "http://localhost:8000"


class PlatformDetectionResponse(BaseModel):
    website_id: str
    detected_platform: PlatformEnum
    confidence: float
    detection_signals: List[str] = []
