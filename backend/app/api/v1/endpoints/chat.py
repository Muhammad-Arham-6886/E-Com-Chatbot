from datetime import datetime
import json
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.chat import ChatSession, ChatMessage
from app.models.enums import RoleEnum
from app.models.user import User
from app.models.website import Website
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    SourceCitationResponse,
    SuggestedActionResponse,
    TestRAGRequest,
    TestRAGResponse,
    ToolCallResponse,
)
from app.services.ai.rag_engine import RAGEngine
from app.services.ai.tool_selector import ToolSelectionEngine
from app.services.org_service import OrganizationService
from app.services.rag.vector_search import VectorSearchService

router = APIRouter(prefix="/chat", tags=["AI Chatbot & RAG Conversations"])


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize or register a new chat conversation session",
)
async def create_chat_session(
    data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Website).where(Website.id == data.website_id)
    website = (await db.execute(stmt)).scalar_one_or_none()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found.",
        )

    session_token = secrets.token_urlsafe(32)
    visitor_id = data.visitor_id or f"vis_{secrets.token_hex(8)}"

    session = ChatSession(
        website_id=website.id,
        organization_id=website.organization_id,
        visitor_id=visitor_id,
        session_token=session_token,
        channel=data.channel,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the AI Assistant and receive grounded RAG response",
)
async def send_chat_message(
    data: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
):
    # 1. Fetch Session
    stmt = (
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.session_token == data.session_token)
    )
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired chat session token.",
        )

    # 2. Fetch Website with settings
    site_stmt = (
        select(Website)
        .options(selectinload(Website.settings))
        .where(Website.id == session.website_id)
    )
    website = (await db.execute(site_stmt)).scalar_one_or_none()
    if not website or website.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Website is currently inactive or unavailable.",
        )

    # 3. Security Guardrails & Prompt Injection Detection
    from app.services.security_guardrails import SecurityGuardrailsEngine
    from app.services.audit_service import AuditLogService

    redacted_content, is_injection, injection_reason = SecurityGuardrailsEngine.process_and_inspect_input(data.content)

    if is_injection:
        await AuditLogService.log_event(
            db,
            action="SECURITY_ALERT_PROMPT_INJECTION",
            resource_type="CHAT_SESSION",
            org_id=website.organization_id,
            resource_id=session.id,
            details={"pattern": injection_reason, "sample": data.content[:120]},
        )
        guardrail_reply = "I cannot fulfill this request as it conflicts with safety and platform security guidelines. How may I help you with our products or store information?"
        bot_msg = ChatMessage(
            session_id=session.id,
            sender="BOT",
            content=guardrail_reply,
            token_count=len(guardrail_reply.split()),
        )
        db.add(bot_msg)
        await db.commit()
        await db.refresh(bot_msg)
        return ChatMessageResponse(
            id=bot_msg.id,
            session_id=session.id,
            sender=bot_msg.sender,
            content=bot_msg.content,
            sources=[],
            suggested_actions=[],
            tool_call=None,
            token_count=bot_msg.token_count,
            created_at=bot_msg.created_at,
        )

    # 4. Store User Message
    user_msg = ChatMessage(
        session_id=session.id,
        sender="USER",
        content=redacted_content,
        token_count=len(redacted_content.split()),
    )
    db.add(user_msg)
    session.last_message_at = datetime.utcnow()
    await db.flush()

    # 5. Execute RAG Engine (if not currently taken over by a human agent)
    if session.status == "HUMAN_TAKEOVER":
        # Do not let AI auto-reply when a human agent has explicitly taken over
        bot_reply_content = "A support agent has joined this conversation and will reply to you shortly."
        bot_msg = ChatMessage(
            session_id=session.id,
            sender="SYSTEM",
            content=bot_reply_content,
            token_count=len(bot_reply_content.split()),
        )
        db.add(bot_msg)
        await db.commit()
        await db.refresh(bot_msg)
        return ChatMessageResponse(
            id=bot_msg.id,
            session_id=session.id,
            sender=bot_msg.sender,
            content=bot_msg.content,
            sources=[],
            suggested_actions=[],
            tool_call=None,
            token_count=bot_msg.token_count,
            created_at=bot_msg.created_at,
        )

    # Check Monthly AI Chat Message Quota
    from app.services.quota_service import QuotaService
    can_chat = await QuotaService.check_monthly_chat_quota(db, website.organization_id)
    if not can_chat:
        quota_msg = "This website has temporarily reached its monthly customer message quota. Please contact support or check back soon."
        bot_msg = ChatMessage(
            session_id=session.id,
            sender="SYSTEM",
            content=quota_msg,
            token_count=len(quota_msg.split()),
        )
        db.add(bot_msg)
        await db.commit()
        await db.refresh(bot_msg)
        return ChatMessageResponse(
            id=bot_msg.id,
            session_id=session.id,
            sender=bot_msg.sender,
            content=bot_msg.content,
            sources=[],
            suggested_actions=[],
            tool_call=None,
            token_count=bot_msg.token_count,
            created_at=bot_msg.created_at,
        )

    rag_engine = RAGEngine(db)
    rag_resp = await rag_engine.process_query(
        user_message=redacted_content,
        website=website,
        chat_history=session.messages,
    )

    if rag_resp.tool_call and rag_resp.tool_call.tool.value == "escalate_to_human":
        session.status = "WAITING_HUMAN"

    # Track usage & tokens consumed
    await QuotaService.increment_chat_usage(db, website.organization_id, tokens=rag_resp.token_count)

    # Sanitize Output
    safe_output_content = SecurityGuardrailsEngine.sanitize_output(rag_resp.content)

    # 6. Store Bot Message
    bot_msg = ChatMessage(
        session_id=session.id,
        sender="BOT",
        content=safe_output_content,
        sources_json=json.dumps([s.to_dict() for s in rag_resp.sources]) if rag_resp.sources else None,
        suggested_actions_json=json.dumps([a.to_dict() for a in rag_resp.suggested_actions])
        if rag_resp.suggested_actions
        else None,
        tool_call_json=json.dumps(rag_resp.tool_call.to_dict()) if rag_resp.tool_call else None,
        token_count=rag_resp.token_count,
    )
    db.add(bot_msg)
    await db.commit()
    await db.refresh(bot_msg)

    sources_out = [
        SourceCitationResponse(title=s.title, url=s.url)
        for s in rag_resp.sources
    ]
    actions_out = [
        SuggestedActionResponse(
            type=a.action_type,
            label=a.label,
            value=a.value,
            payload=a.payload,
        )
        for a in rag_resp.suggested_actions
    ]
    tool_out = ToolCallResponse(
        tool=rag_resp.tool_call.tool.value,
        parameters=rag_resp.tool_call.parameters,
        confidence=rag_resp.tool_call.confidence,
    )

    return ChatMessageResponse(
        id=bot_msg.id,
        session_id=session.id,
        sender=bot_msg.sender,
        content=bot_msg.content,
        sources=sources_out,
        suggested_actions=actions_out,
        tool_call=tool_out,
        token_count=bot_msg.token_count,
        created_at=bot_msg.created_at,
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[ChatMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get conversation history for a chat session",
)
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = (await db.execute(stmt)).scalars().all()

    results: List[ChatMessageResponse] = []
    for msg in messages:
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

        results.append(
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

    return results


@router.post(
    "/test-rag",
    response_model=TestRAGResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard test tool for RAG prompt synthesis, vector grounding, and tool inspection",
)
async def test_rag_debug(
    data: TestRAGRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    site_stmt = (
        select(Website)
        .options(selectinload(Website.settings))
        .where(and_(Website.id == data.website_id, Website.organization_id == org_id))
    )
    website = (await db.execute(site_stmt)).scalar_one_or_none()
    if not website:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    rag_engine = RAGEngine(db)
    rag_resp = await rag_engine.process_query(data.message, website)

    # Retrieve vector search chunks for debug inspection
    vector_search = VectorSearchService(db)
    debug_hits = await vector_search.search(
        query=data.message,
        org_id=org_id,
        website_id=website.id,
        top_k=4,
        min_similarity=0.05,
    )
    debug_chunks = [f"[{h.title}] ({h.url}) (Score: {h.similarity_score:.2f}):\n{h.content}" for h in debug_hits]
    system_prompt = rag_engine._build_grounded_system_prompt(website, [h.content for h in debug_hits])

    return TestRAGResponse(
        user_message=data.message,
        reply=rag_resp.content,
        sources=[SourceCitationResponse(title=s.title, url=s.url) for s in rag_resp.sources],
        suggested_actions=[
            SuggestedActionResponse(type=a.action_type, label=a.label, value=a.value, payload=a.payload)
            for a in rag_resp.suggested_actions
        ],
        tool_call=ToolCallResponse(
            tool=rag_resp.tool_call.tool.value,
            parameters=rag_resp.tool_call.parameters,
            confidence=rag_resp.tool_call.confidence,
        ),
        debug_context_chunks=debug_chunks,
        system_prompt=system_prompt if data.include_debug else None,
    )
