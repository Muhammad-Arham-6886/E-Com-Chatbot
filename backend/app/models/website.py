import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import PlatformEnum, WebsiteStatusEnum

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.crawling import CrawlJob, KnowledgeDocument


class Website(Base, TimestampMixin):
    __tablename__ = "websites"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    domain: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    public_site_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    platform: Mapped[PlatformEnum] = mapped_column(
        SQLEnum(PlatformEnum),
        default=PlatformEnum.UNKNOWN,
        nullable=False,
    )
    status: Mapped[WebsiteStatusEnum] = mapped_column(
        SQLEnum(WebsiteStatusEnum),
        default=WebsiteStatusEnum.ACTIVE,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="websites",
    )
    settings: Mapped[Optional["WebsiteSettings"]] = relationship(
        "WebsiteSettings",
        back_populates="website",
        uselist=False,
        cascade="all, delete-orphan",
    )
    domains: Mapped[List["WebsiteDomain"]] = relationship(
        "WebsiteDomain",
        back_populates="website",
        cascade="all, delete-orphan",
    )
    crawl_jobs: Mapped[List["CrawlJob"]] = relationship(
        "CrawlJob",
        back_populates="website",
        cascade="all, delete-orphan",
    )
    knowledge_documents: Mapped[List["KnowledgeDocument"]] = relationship(
        "KnowledgeDocument",
        back_populates="website",
        cascade="all, delete-orphan",
    )


class WebsiteSettings(Base, TimestampMixin):
    __tablename__ = "website_settings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    website_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("websites.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    chatbot_name: Mapped[str] = mapped_column(
        String(255),
        default="AI Assistant",
        nullable=False,
    )
    welcome_message: Mapped[str] = mapped_column(
        Text,
        default="Hi there! How can I help you today?",
        nullable=False,
    )
    placeholder_text: Mapped[str] = mapped_column(
        String(255),
        default="Type your message here...",
        nullable=False,
    )
    primary_color: Mapped[str] = mapped_column(
        String(32),
        default="#4F46E5",
        nullable=False,
    )
    secondary_color: Mapped[str] = mapped_column(
        String(32),
        default="#1E1B4B",
        nullable=False,
    )
    launcher_position: Mapped[str] = mapped_column(
        String(32),
        default="bottom-right",
        nullable=False,
    )
    widget_size: Mapped[str] = mapped_column(
        String(32),
        default="medium",
        nullable=False,
    )
    border_radius: Mapped[str] = mapped_column(
        String(32),
        default="16px",
        nullable=False,
    )
    enable_whatsapp: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    whatsapp_number: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    whatsapp_custom_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    whatsapp_handoff_trigger: Mapped[str] = mapped_column(
        String(32),
        default="ON_ESCALATION",  # "ON_ESCALATION", "ALWAYS_VISIBLE", "DISABLED"
        nullable=False,
    )
    custom_instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="settings",
    )


class WebsiteDomain(Base, TimestampMixin):
    __tablename__ = "website_domains"

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
    domain: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="domains",
    )
