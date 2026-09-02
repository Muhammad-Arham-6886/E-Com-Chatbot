from typing import Optional
from pydantic import BaseModel, Field


class WhatsAppPreviewRequest(BaseModel):
    phone_number: str = Field(..., min_length=5, description="Raw phone number with country code")
    custom_template: Optional[str] = Field(None, description="Custom message template with variable tags")
    visitor_id: Optional[str] = Field(default="visitor_preview_123")
    sample_inquiry: Optional[str] = Field(default="Do you have warranty on custom orders?")


class WhatsAppPreviewResponse(BaseModel):
    is_valid_phone: bool
    clean_phone: str
    formatted_message: str
    preview_url: str
