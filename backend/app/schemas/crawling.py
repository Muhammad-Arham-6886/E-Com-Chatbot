from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import CrawlJobStatusEnum, CrawlPageStatusEnum, DocumentStatusEnum


class CrawlJobStart(BaseModel):
    max_pages: int = Field(default=50, ge=1, le=5000, description="Maximum number of pages to crawl")


class CrawlJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    website_id: str
    organization_id: str
    status: CrawlJobStatusEnum
    total_pages_discovered: int
    total_pages_crawled: int
    total_pages_failed: int
    max_pages: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CrawlPageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    crawl_job_id: str
    website_id: str
    url: str
    status: CrawlPageStatusEnum
    status_code: Optional[int] = None
    page_title: Optional[str] = None
    content_hash: Optional[str] = None
    error: Optional[str] = None
    discovered_via: str
    depth: int
    created_at: datetime


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    website_id: str
    organization_id: str
    crawl_page_id: Optional[str] = None
    url: str
    title: str
    meta_description: Optional[str] = None
    raw_content: str
    content_hash: str
    token_count: int
    status: DocumentStatusEnum
    created_at: datetime
    updated_at: datetime
