import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import CrawlJobStatusEnum, CrawlPageStatusEnum, DocumentStatusEnum

if TYPE_CHECKING:
    from app.models.website import Website
    from app.models.organization import Organization
    from app.models.chunk import DocumentChunk


class CrawlJob(Base, TimestampMixin):
    __tablename__ = "crawl_jobs"

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
    status: Mapped[CrawlJobStatusEnum] = mapped_column(
        SQLEnum(CrawlJobStatusEnum),
        default=CrawlJobStatusEnum.PENDING,
        nullable=False,
        index=True,
    )
    total_pages_discovered: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_pages_crawled: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_pages_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_pages: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="crawl_jobs",
    )
    pages: Mapped[List["CrawlPage"]] = relationship(
        "CrawlPage",
        back_populates="crawl_job",
        cascade="all, delete-orphan",
    )


class CrawlPage(Base, TimestampMixin):
    __tablename__ = "crawl_pages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    crawl_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    website_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        index=True,
    )
    status: Mapped[CrawlPageStatusEnum] = mapped_column(
        SQLEnum(CrawlPageStatusEnum),
        default=CrawlPageStatusEnum.DISCOVERED,
        nullable=False,
        index=True,
    )
    status_code: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    page_title: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    discovered_via: Mapped[str] = mapped_column(
        String(64),
        default="sitemap",
        nullable=False,
    )
    depth: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Relationships
    crawl_job: Mapped["CrawlJob"] = relationship(
        "CrawlJob",
        back_populates="pages",
    )
    document: Mapped[Optional["KnowledgeDocument"]] = relationship(
        "KnowledgeDocument",
        back_populates="crawl_page",
        uselist=False,
    )


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"

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
    crawl_page_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("crawl_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    meta_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    raw_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    status: Mapped[DocumentStatusEnum] = mapped_column(
        SQLEnum(DocumentStatusEnum),
        default=DocumentStatusEnum.RAW,
        nullable=False,
    )

    # Relationships
    crawl_page: Mapped[Optional["CrawlPage"]] = relationship(
        "CrawlPage",
        back_populates="document",
    )
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="knowledge_documents",
    )
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )
