from datetime import datetime
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import RoleEnum
from app.models.integration import CommerceIntegration
from app.models.user import User
from app.models.website import Website
from app.schemas.integration import (
    ProductCardResponse,
    WooCommerceConnectRequest,
    WooCommerceIntegrationResponse,
    WooCommerceTestResponse,
)
from app.services.ai.commerce_provider import WooCommerceProvider
from app.services.org_service import OrganizationService

router = APIRouter(prefix="/integrations", tags=["E-Commerce Integrations & WooCommerce"])


def mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


async def verify_admin_access(db: AsyncSession, org_id: str, user_id: str):
    member = await OrganizationService.get_member(db, org_id, user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. Not an organization member.",
        )
    if member.role not in [RoleEnum.OWNER, RoleEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires OWNER or ADMIN role.",
        )
    return member


@router.post(
    "/woocommerce/connect",
    response_model=WooCommerceIntegrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect or update WooCommerce REST API credentials for a website",
)
async def connect_woocommerce(
    data: WooCommerceConnectRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_admin_access(db, org_id, current_user.id)

    # 1. Verify Website
    site_stmt = select(Website).where(
        and_(Website.id == data.website_id, Website.organization_id == org_id)
    )
    website = (await db.execute(site_stmt)).scalar_one_or_none()
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Website not found in this organization.",
        )

    # 2. Test Live Connection
    provider = WooCommerceProvider(
        api_url=data.api_url,
        consumer_key=data.consumer_key,
        consumer_secret=data.consumer_secret,
    )
    test_result = await provider.test_connection()
    if not test_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"WooCommerce connection failed: {test_result.get('message')}",
        )

    # 3. Create or Update Integration Record
    stmt = select(CommerceIntegration).where(CommerceIntegration.website_id == website.id)
    integration = (await db.execute(stmt)).scalar_one_or_none()

    metadata = {
        "currency": test_result.get("currency", "USD"),
        "product_count": test_result.get("product_count", 0),
        "last_test_message": test_result.get("message"),
    }

    if integration:
        integration.api_url = data.api_url.rstrip("/")
        integration.consumer_key = data.consumer_key
        integration.consumer_secret = data.consumer_secret
        integration.is_active = data.is_active
        integration.last_sync_at = datetime.utcnow()
        integration.metadata_json = json.dumps(metadata)
    else:
        integration = CommerceIntegration(
            website_id=website.id,
            organization_id=org_id,
            platform="WOOCOMMERCE",
            api_url=data.api_url.rstrip("/"),
            consumer_key=data.consumer_key,
            consumer_secret=data.consumer_secret,
            is_active=data.is_active,
            last_sync_at=datetime.utcnow(),
            metadata_json=json.dumps(metadata),
        )
        db.add(integration)

    await db.commit()
    await db.refresh(integration)

    return WooCommerceIntegrationResponse(
        id=integration.id,
        website_id=integration.website_id,
        organization_id=integration.organization_id,
        platform=integration.platform,
        api_url=integration.api_url,
        consumer_key_masked=mask_key(integration.consumer_key),
        is_active=integration.is_active,
        last_sync_at=integration.last_sync_at,
        metadata_json=integration.metadata_json,
        created_at=integration.created_at,
    )


@router.get(
    "/woocommerce/{website_id}",
    response_model=Optional[WooCommerceIntegrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current WooCommerce integration status for a website",
)
async def get_woocommerce_integration(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    stmt = select(CommerceIntegration).where(
        and_(
            CommerceIntegration.website_id == website_id,
            CommerceIntegration.organization_id == org_id,
        )
    )
    integration = (await db.execute(stmt)).scalar_one_or_none()
    if not integration:
        return None

    return WooCommerceIntegrationResponse(
        id=integration.id,
        website_id=integration.website_id,
        organization_id=integration.organization_id,
        platform=integration.platform,
        api_url=integration.api_url,
        consumer_key_masked=mask_key(integration.consumer_key),
        is_active=integration.is_active,
        last_sync_at=integration.last_sync_at,
        metadata_json=integration.metadata_json,
        created_at=integration.created_at,
    )


@router.post(
    "/woocommerce/{website_id}/test",
    response_model=WooCommerceTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Test live WooCommerce connection and retrieve sample products",
)
async def test_woocommerce_integration(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_admin_access(db, org_id, current_user.id)

    stmt = select(CommerceIntegration).where(
        and_(
            CommerceIntegration.website_id == website_id,
            CommerceIntegration.organization_id == org_id,
        )
    )
    integration = (await db.execute(stmt)).scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WooCommerce integration not configured for this website.",
        )

    provider = WooCommerceProvider(
        api_url=integration.api_url,
        consumer_key=integration.consumer_key,
        consumer_secret=integration.consumer_secret,
    )
    test_result = await provider.test_connection()
    sample_products = await provider.search_products(query="", limit=3)

    return WooCommerceTestResponse(
        success=test_result.get("success", False),
        status_code=test_result.get("status_code", 200),
        message=test_result.get("message", "Connection tested."),
        currency=test_result.get("currency", "USD"),
        product_count=test_result.get("product_count", len(sample_products)),
        sample_products=[
            ProductCardResponse(
                id=p.id,
                name=p.name,
                price=p.price,
                currency=p.currency,
                description=p.description,
                image_url=p.image_url,
                product_url=p.product_url,
                in_stock=p.in_stock,
            )
            for p in sample_products
        ],
    )


@router.delete(
    "/woocommerce/{website_id}",
    status_code=status.HTTP_200_OK,
    summary="Disconnect WooCommerce integration from website",
)
async def disconnect_woocommerce(
    website_id: str,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_admin_access(db, org_id, current_user.id)

    stmt = select(CommerceIntegration).where(
        and_(
            CommerceIntegration.website_id == website_id,
            CommerceIntegration.organization_id == org_id,
        )
    )
    integration = (await db.execute(stmt)).scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found.",
        )

    await db.delete(integration)
    await db.commit()
    return {"message": "WooCommerce integration disconnected successfully."}
