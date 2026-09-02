from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SourceCitationResponse(BaseModel):
    title: str
    url: str


class SuggestedActionResponse(BaseModel):
    type: str
    label: str
    value: str
    payload: Optional[Dict[str, Any]] = None


class ToolCallResponse(BaseModel):
    tool: str
    parameters: Dict[str, Any]
    confidence: float


class ChatSessionCreate(BaseModel):
    website_id: str
    visitor_id: Optional[str] = None
    channel: str = Field(default="WEB_WIDGET", description="Channel e.g. WEB_WIDGET or DASHBOARD_TEST")


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    website_id: str
    organization_id: str
    visitor_id: str
    session_token: str
    channel: str
    status: str
    assigned_user_id: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime


class ChatMessageCreate(BaseModel):
    session_token: str
    content: str = Field(..., min_length=1, max_length=2000, description="User message text")


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    sender: str
    content: str
    sources: List[SourceCitationResponse] = Field(default_factory=list)
    suggested_actions: List[SuggestedActionResponse] = Field(default_factory=list)
    tool_call: Optional[ToolCallResponse] = None
    token_count: int
    created_at: datetime


class TestRAGRequest(BaseModel):
    website_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    include_debug: bool = True


class TestRAGResponse(BaseModel):
    user_message: str
    reply: str
    sources: List[SourceCitationResponse]
    suggested_actions: List[SuggestedActionResponse]
    tool_call: ToolCallResponse
    debug_context_chunks: List[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None


class ConversationSummaryResponse(BaseModel):
    id: str
    website_id: str
    website_name: str
    website_domain: str
    visitor_id: str
    status: str
    channel: str
    message_count: int
    last_message_preview: Optional[str] = None
    last_message_sender: Optional[str] = None
    last_message_at: Optional[datetime] = None
    assigned_user_id: Optional[str] = None
    assigned_user_name: Optional[str] = None
    created_at: datetime


class PaginatedConversationsResponse(BaseModel):
    items: List[ConversationSummaryResponse]
    total: int
    page: int
    limit: int
    pages: int


class ConversationDetailResponse(BaseModel):
    session: ChatSessionResponse
    website_name: str
    website_domain: str
    assigned_user_name: Optional[str] = None
    messages: List[ChatMessageResponse]


class UpdateConversationStatusRequest(BaseModel):
    status: str = Field(..., description="BOT_ACTIVE | WAITING_HUMAN | HUMAN_TAKEOVER | CLOSED")


class AgentReplyRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=3000, description="Agent message text")


class AssignConversationRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Assigned User UUID or null to unassign")
