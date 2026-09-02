from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: Optional[str] = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    user: Optional[AuditLogUserSummary] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime


class PaginatedAuditLogsResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    limit: int


class GuardrailTestRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to scan for injection/PII")


class GuardrailTestResponse(BaseModel):
    original_text: str
    redacted_text: str
    is_prompt_injection: bool
    injection_reason: Optional[str] = None
    sanitized_output_preview: str
