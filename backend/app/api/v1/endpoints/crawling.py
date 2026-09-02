import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.crawling import CrawlJob, CrawlPage, KnowledgeDocument
from app.models.enums import CrawlJobStatusEnum, RoleEnum
from app.models.user import User
from app.models.website import Website
from app.schemas.auth import MessageResponse
from app.schemas.crawling import (
    CrawlJobResponse,
    CrawlJobStart,
    CrawlPageResponse,
    KnowledgeDocumentResponse,
)
from app.services.crawler.crawler_engine import CrawlerEngine
from app.services.org_service import OrganizationService
from app.services.website_service import WebsiteService
from app.tasks.crawl_tasks import run_crawl_job

logger = logging.getLogger("ai_commerce_saas.crawling")

router = APIRouter(prefix="/crawling", tags=["Website Crawler & Discovery"])


def _execute_crawl_job(job_id: str):
    """Run crawl synchronously in a background thread (called by FastAPI BackgroundTasks)."""
    try:
        run_crawl_job(job_id)
    except Exception as exc:
        logger.error(f"Background crawl execution failed for job {job_id}: {exc}", exc_info=True)


async def verify_website_access(
    db: AsyncSession, website_id: str, org_id: str, user_id: str, min_role: RoleEnum = RoleEnum.VIEWER
) -> Website:
    # 1. Verify organization membership & role
    member = await OrganizationService.get_member(db, org_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization.",
        )
    if not member.role.has_permission(min_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Action requires at least '{min_role.value}' role, but your role is '{member.role.value}'.",
        )

    # 2. Verify website belongs to organization
    website = await WebsiteService.get_website(db, website_id, org_id)
    return website


@router.post(
    "/websites/{website_id}/start",
    response_model=CrawlJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new background crawling and content discovery job",
)
async def start_crawl_job(
    website_id: str,
    data: CrawlJobStart,
    background_tasks: BackgroundTasks,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    website = await verify_website_access(db, website_id, org_id, current_user.id, RoleEnum.ADMIN)

    # Check if there is already an active crawl job running.
    # Auto-expire stale jobs stuck for more than 5 minutes.
    STALE_THRESHOLD_MINUTES = 5
    active_stmt = select(CrawlJob).where(
        and_(
            CrawlJob.website_id == website_id,
            CrawlJob.status.in_([CrawlJobStatusEnum.PENDING, CrawlJobStatusEnum.RUNNING]),
        )
    )
    active_job = (await db.execute(active_stmt)).scalar_one_or_none()
    if active_job:
        job_age = datetime.now(timezone.utc) - active_job.created_at.replace(tzinfo=timezone.utc)
        if job_age > timedelta(minutes=STALE_THRESHOLD_MINUTES):
            logger.warning(
                f"Auto-expiring stale crawl job {active_job.id} (status={active_job.status.value}, "
                f"age={job_age.total_seconds():.0f}s). Marking as FAILED."
            )
            active_job.status = CrawlJobStatusEnum.FAILED
            active_job.error_message = f"Auto-expired after {STALE_THRESHOLD_MINUTES} minutes with no completion."
            active_job.completed_at = datetime.now(timezone.utc)
            await db.commit()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A crawl job is already in progress (Job ID: {active_job.id}). Please wait for it to complete or cancel it.",
            )

    # Create new CrawlJob
    job = CrawlJob(
        website_id=website.id,
        organization_id=org_id,
        status=CrawlJobStatusEnum.PENDING,
        max_pages=data.max_pages,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Run the crawl in a background task so the HTTP response returns immediately.
    # When Celery has Redis, .delay() dispatches async. When task_always_eager (no Redis),
    # .delay() would block — so we always use FastAPI BackgroundTasks for reliability.
    background_tasks.add_task(_execute_crawl_job, job.id)

    return job


@router.get(
    "/jobs/{job_id}",
    response_model=CrawlJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get crawl job status, statistics, and progress",
)
async def get_crawl_job_status(
    job_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CrawlJob).where(and_(CrawlJob.id == job_id, CrawlJob.organization_id == org_id))
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crawl job not found or does not belong to your organization.",
        )

    # Verify user access to org
    await OrganizationService.get_member(db, org_id, current_user.id)
    return job


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=CrawlJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an in-progress crawl job",
)
async def cancel_crawl_job(
    job_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CrawlJob).where(and_(CrawlJob.id == job_id, CrawlJob.organization_id == org_id))
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crawl job not found.",
        )

    # Verify ADMIN+ role
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member or not member.role.has_permission(RoleEnum.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cancelling a crawl job requires ADMIN or OWNER role.",
        )

    if job.status in (CrawlJobStatusEnum.PENDING, CrawlJobStatusEnum.RUNNING):
        job.status = CrawlJobStatusEnum.CANCELLED
        await db.commit()
        await db.refresh(job)

    return job


@router.get(
    "/websites/{website_id}/pages",
    response_model=List[CrawlPageResponse],
    status_code=status.HTTP_200_OK,
    summary="List all discovered and crawled pages for a website",
)
async def list_crawled_pages(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_website_access(db, website_id, org_id, current_user.id, RoleEnum.VIEWER)

    stmt = (
        select(CrawlPage)
        .where(CrawlPage.website_id == website_id)
        .order_by(desc(CrawlPage.created_at))
        .limit(200)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/websites/{website_id}/documents",
    response_model=List[KnowledgeDocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List all clean extracted knowledge documents for a website",
)
async def list_knowledge_documents(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_website_access(db, website_id, org_id, current_user.id, RoleEnum.VIEWER)

    stmt = (
        select(KnowledgeDocument)
        .where(
            and_(
                KnowledgeDocument.website_id == website_id,
                KnowledgeDocument.organization_id == org_id,
            )
        )
        .order_by(desc(KnowledgeDocument.created_at))
        .limit(200)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
