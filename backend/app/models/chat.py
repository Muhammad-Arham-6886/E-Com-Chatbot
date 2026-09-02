import json
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.website import Website
    from app.models.organization import Organization
    from app.models.user import User


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    website_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visitor_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    session_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(
        String(32),
        default="WEB_WIDGET",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="BOT_ACTIVE",  # "BOT_ACTIVE", "WAITING_HUMAN", "HUMAN_TAKEOVER", "CLOSED"
        nullable=False,
        index=True,
    )
    assigned_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    website: Mapped["Website"] = relationship("Website")
    assigned_user: Mapped[Optional["User"]] = relationship("User")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(
        String(16),
        nullable=False,  # "USER", "BOT", "AGENT", "SYSTEM"
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sources_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    suggested_actions_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    tool_call_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages",
    )
