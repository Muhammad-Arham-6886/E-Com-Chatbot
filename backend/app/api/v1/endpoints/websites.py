from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import RoleEnum
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.website import (
    PlatformDetectionResponse,
    PublicWidgetConfigResponse,
    WebsiteCreate,
    WebsiteDetailResponse,
    WebsiteResponse,
    WebsiteSettingsResponse,
    WebsiteSettingsUpdate,
    WebsiteUpdate,
)
from app.services.org_service import OrganizationService
from app.services.website_service import WebsiteService
from fastapi import HTTPException

router = APIRouter(prefix="/websites", tags=["Websites & Channels"])


async def verify_org_access(
    db: AsyncSession, org_id: str, user_id: str, min_role: RoleEnum = RoleEnum.VIEWER
) -> OrganizationMember:
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
    return member


@router.post(
    "",
    response_model=WebsiteDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new website to an organization",
)
async def create_website(
    data: WebsiteCreate,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.ADMIN)
    website = await WebsiteService.create_website(db, org_id, data)
    return website


@router.get(
    "",
    response_model=List[WebsiteResponse],
    status_code=status.HTTP_200_OK,
    summary="List all websites belonging to an organization",
)
async def list_websites(
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.VIEWER)
    websites = await WebsiteService.list_websites(db, org_id)
    return websites


@router.get(
    "/{website_id}",
    response_model=WebsiteDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get website details, settings, and domains",
)
async def get_website(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.VIEWER)
    website = await WebsiteService.get_website(db, website_id, org_id)
    return website


@router.put(
    "/{website_id}",
    response_model=WebsiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Update website basic properties",
)
async def update_website(
    website_id: str,
    data: WebsiteUpdate,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.ADMIN)
    website = await WebsiteService.update_website(db, website_id, org_id, data)
    return website


@router.delete(
    "/{website_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a website and its associated settings",
)
async def delete_website(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.ADMIN)
    await WebsiteService.delete_website(db, website_id, org_id)
    return {"message": "Website deleted successfully"}


@router.get(
    "/{website_id}/settings",
    response_model=WebsiteSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get widget appearance settings for a website",
)
async def get_website_settings(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.VIEWER)
    website = await WebsiteService.get_website(db, website_id, org_id)
    return website.settings


@router.put(
    "/{website_id}/settings",
    response_model=WebsiteSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update widget appearance settings for a website",
)
async def update_website_settings(
    website_id: str,
    data: WebsiteSettingsUpdate,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.ADMIN)
    settings = await WebsiteService.update_settings(db, website_id, org_id, data)
    return settings


@router.post(
    "/{website_id}/detect-platform",
    response_model=PlatformDetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run live platform detection scan on a website URL",
)
async def detect_website_platform(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(db, org_id, current_user.id, RoleEnum.ADMIN)
    res = await WebsiteService.detect_website_platform(db, website_id, org_id)
    return res


# Public Endpoint (Unauthenticated) for Chatbot Widget
@router.get(
    "/public/{public_site_id}/config",
    response_model=PublicWidgetConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Public endpoint for embeddable JavaScript widget to fetch UI configuration",
)
async def get_public_widget_config(
    public_site_id: str,
    db: AsyncSession = Depends(get_db),
):
    config = await WebsiteService.get_public_config(db, public_site_id)
    return config
