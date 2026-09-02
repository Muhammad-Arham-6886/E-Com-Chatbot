from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import RoleEnum
from app.models.user import User
from app.models.website import Website
from app.services.org_service import OrganizationService
from app.services.plugin_service import WordPressPluginService

router = APIRouter(tags=["WordPress & WooCommerce Integration Plugin"])


@router.get(
    "/websites/{website_id}/download-plugin",
    status_code=status.HTTP_200_OK,
    summary="Download pre-configured WordPress & WooCommerce integration plugin zip",
)
async def download_wordpress_plugin(
    request: Request,
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. You are not a member of this organization.",
        )

    stmt = select(Website).where(
        and_(Website.id == website_id, Website.organization_id == org_id)
    )
    website = (await db.execute(stmt)).scalar_one_or_none()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found in this organization.",
        )

    # Derive base URL from incoming request
    base_url = str(request.base_url).rstrip("/")
    if "localhost" in base_url or "127.0.0.1" in base_url:
        # Default local dev port
        api_url = "http://localhost:8000"
    else:
        api_url = base_url

    zip_bytes = WordPressPluginService.generate_plugin_zip(website=website, api_url=api_url)
    clean_domain = website.domain.replace(".", "-")
    filename = f"ai-commerce-assistant-{clean_domain}.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/zip",
        },
    )
