from datetime import datetime
import json
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.chat import ChatSession, ChatMessage
from app.models.enums import RoleEnum
from app.models.user import User
from app.models.website import Website
from app.schemas.chat import (
    AgentReplyRequest,
    AssignConversationRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    ConversationDetailResponse,
    ConversationSummaryResponse,
    PaginatedConversationsResponse,
    SourceCitationResponse,
    SuggestedActionResponse,
    ToolCallResponse,
    UpdateConversationStatusRequest,
)
from app.services.org_service import OrganizationService

router = APIRouter(prefix="/conversations", tags=["Live Visitor Conversations & Agent Inbox"])


async def verify_org_membership(db: AsyncSession, org_id: str, user_id: str, min_role: RoleEnum = RoleEnum.VIEWER):
    member = await OrganizationService.get_member(db, org_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. You are not a member of this organization.",
        )
    role_hierarchy = {
        RoleEnum.VIEWER: 1,
        RoleEnum.AGENT: 2,
        RoleEnum.MANAGER: 3,
        RoleEnum.ADMIN: 4,
        RoleEnum.OWNER: 5,
    }
    if role_hierarchy.get(member.role, 0) < role_hierarchy.get(min_role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Minimum role required: {min_role.value}",
        )
    return member


@router.get(
    "",
    response_model=PaginatedConversationsResponse,
    status_code=status.HTTP_200_OK,
    summary="List all visitor conversations with status filtering and pagination",
)
async def list_conversations(
    org_id: str = Query(..., description="Organization UUID"),
    website_id: Optional[str] = Query(None, description="Filter by website UUID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (BOT_ACTIVE, WAITING_HUMAN, HUMAN_TAKEOVER, CLOSED)"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    search: Optional[str] = Query(None, description="Search by visitor ID or keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_membership(db, org_id, current_user.id, RoleEnum.VIEWER)

    filters = [ChatSession.organization_id == org_id]
    if website_id:
        filters.append(ChatSession.website_id == website_id)
    if status_filter:
        filters.append(ChatSession.status == status_filter)
    if channel:
        filters.append(ChatSession.channel == channel)
    if search:
        filters.append(ChatSession.visitor_id.ilike(f"%{search}%"))

    # Count total
    count_stmt = select(func.count(ChatSession.id)).where(and_(*filters))
    total = (await db.execute(count_stmt)).scalar_one() or 0

    # Query items
    offset = (page - 1) * limit
    stmt = (
        select(ChatSession)
        .options(
            selectinload(ChatSession.website),
            selectinload(ChatSession.assigned_user),
            selectinload(ChatSession.messages),
        )
        .where(and_(*filters))
        .order_by(desc(ChatSession.last_message_at), desc(ChatSession.created_at))
        .offset(offset)
        .limit(limit)
    )
    sessions = (await db.execute(stmt)).scalars().all()

    items: List[ConversationSummaryResponse] = []
    for s in sessions:
        last_msg = s.messages[-1] if s.messages else None
        items.append(
            ConversationSummaryResponse(
                id=s.id,
                website_id=s.website_id,
                website_name=s.website.name if s.website else "Unknown Store",
                website_domain=s.website.domain if s.website else "",
                visitor_id=s.visitor_id,
                status=s.status,
                channel=s.channel,
                message_count=len(s.messages),
                last_message_preview=last_msg.content[:120] if last_msg else None,
                last_message_sender=last_msg.sender if last_msg else None,
                last_message_at=s.last_message_at or s.created_at,
                assigned_user_id=s.assigned_user_id,
                assigned_user_name=s.assigned_user.full_name if s.assigned_user else None,
                created_at=s.created_at,
            )
        )

    pages = math.ceil(total / limit) if total > 0 else 1
    return PaginatedConversationsResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get(
    "/{session_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full conversation transcript and visitor session details",
)
async def get_conversation_detail(
    session_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_membership(db, org_id, current_user.id, RoleEnum.VIEWER)

    stmt = (
        select(ChatSession)
        .options(
            selectinload(ChatSession.website),
            selectinload(ChatSession.assigned_user),
            selectinload(ChatSession.messages),
        )
        .where(and_(ChatSession.id == session_id, ChatSession.organization_id == org_id))
    )
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        )

    messages_out: List[ChatMessageResponse] = []
    for msg in session.messages:
        sources_list = []
        if msg.sources_json:
            try:
                raw_sources = json.loads(msg.sources_json)
                sources_list = [SourceCitationResponse(title=s["title"], url=s["url"]) for s in raw_sources]
            except Exception:
                pass

        actions_list = []
        if msg.suggested_actions_json:
            try:
                raw_actions = json.loads(msg.suggested_actions_json)
                actions_list = [
                    SuggestedActionResponse(
                        type=a["type"],
                        label=a["label"],
                        value=a["value"],
                        payload=a.get("payload"),
                    )
                    for a in raw_actions
                ]
            except Exception:
                pass

        tool_obj = None
        if msg.tool_call_json:
            try:
                raw_tool = json.loads(msg.tool_call_json)
                tool_obj = ToolCallResponse(
                    tool=raw_tool["tool"],
                    parameters=raw_tool["parameters"],
                    confidence=raw_tool["confidence"],
                )
            except Exception:
                pass

        messages_out.append(
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                sender=msg.sender,
                content=msg.content,
                sources=sources_list,
                suggested_actions=actions_list,
                tool_call=tool_obj,
                token_count=msg.token_count,
                created_at=msg.created_at,
            )
        )

    session_res = ChatSessionResponse(
        id=session.id,
        website_id=session.website_id,
        organization_id=session.organization_id,
        visitor_id=session.visitor_id,
        session_token=session.session_token,
        channel=session.channel,
        status=session.status,
        assigned_user_id=session.assigned_user_id,
        last_message_at=session.last_message_at,
        created_at=session.created_at,
    )

    return ConversationDetailResponse(
        session=session_res,
        website_name=session.website.name if session.website else "Store",
        website_domain=session.website.domain if session.website else "",
        assigned_user_name=session.assigned_user.full_name if session.assigned_user else None,
        messages=messages_out,
    )


@router.put(
    "/{session_id}/status",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update conversation status (e.g. human takeover, resume bot, or close)",
)
async def update_conversation_status(
    session_id: str,
    data: UpdateConversationStatusRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_membership(db, org_id, current_user.id, RoleEnum.AGENT)

    stmt = select(ChatSession).where(and_(ChatSession.id == session_id, ChatSession.organization_id == org_id))
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        )

    session.status = data.status
    await db.commit()
    await db.refresh(session)
    return session


@router.post(
    "/{session_id}/agent-reply",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a human agent message directly into the visitor chat thread",
)
async def send_agent_reply(
    session_id: str,
    data: AgentReplyRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_membership(db, org_id, current_user.id, RoleEnum.AGENT)

    stmt = select(ChatSession).where(and_(ChatSession.id == session_id, ChatSession.organization_id == org_id))
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        )

    # Automatically mark session as HUMAN_TAKEOVER and assign to current agent if unassigned
    session.status = "HUMAN_TAKEOVER"
    if not session.assigned_user_id:
        session.assigned_user_id = current_user.id
    session.last_message_at = datetime.utcnow()

    agent_msg = ChatMessage(
        session_id=session.id,
        sender="AGENT",
        content=data.content,
        token_count=len(data.content.split()),
    )
    db.add(agent_msg)
    await db.commit()
    await db.refresh(agent_msg)

    return ChatMessageResponse(
        id=agent_msg.id,
        session_id=session.id,
        sender=agent_msg.sender,
        content=agent_msg.content,
        sources=[],
        suggested_actions=[],
        tool_call=None,
        token_count=agent_msg.token_count,
        created_at=agent_msg.created_at,
    )


@router.put(
    "/{session_id}/assign",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign a conversation session to a support agent",
)
async def assign_conversation(
    session_id: str,
    data: AssignConversationRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_membership(db, org_id, current_user.id, RoleEnum.AGENT)

    stmt = select(ChatSession).where(and_(ChatSession.id == session_id, ChatSession.organization_id == org_id))
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation session not found.",
        )

    session.assigned_user_id = data.user_id
    await db.commit()
    await db.refresh(session)
    return session
