from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import RoleEnum
from app.models.subscription import SubscriptionTierEnum, SubscriptionStatusEnum
from app.models.user import User
from app.schemas.billing import (
    UsageBreakdownResponse,
    SubscriptionResponse,
    PlanTierInfo,
    ChangeTierRequest,
)
from app.services.org_service import OrganizationService
from app.services.quota_service import QuotaService, TIER_LIMITS

router = APIRouter(prefix="/billing", tags=["Multi-Tenant Quotas & Billing"])


@router.get(
    "/tiers",
    response_model=List[PlanTierInfo],
    summary="Get all available subscription plan tiers and quota limits",
)
async def get_all_tiers():
    tiers_list = []
    for tier_enum, info in TIER_LIMITS.items():
        tiers_list.append(
            PlanTierInfo(
                tier=tier_enum.value,
                name=info["name"],
                price_monthly=info["price_monthly"],
                max_websites=info["max_websites"],
                max_pages_per_crawl=info["max_pages_per_crawl"],
                max_chunks=info["max_chunks"],
                max_monthly_messages=info["max_monthly_messages"],
                rate_limit_rpm=info["rate_limit_rpm"],
                features=info["features"],
            )
        )
    return tiers_list


@router.get(
    "/usage",
    response_model=UsageBreakdownResponse,
    summary="Get organization current usage metrics, limits, and progress percentages",
)
async def get_organization_usage(
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

    data = await QuotaService.get_usage_breakdown(db, org_id)
    return UsageBreakdownResponse(**data)


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get active subscription details for organization",
)
async def get_organization_subscription(
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

    sub = await QuotaService.get_or_create_subscription(db, org_id)
    return SubscriptionResponse.model_validate(sub)


@router.post(
    "/change-tier",
    response_model=SubscriptionResponse,
    summary="Upgrade or change subscription plan tier",
)
async def change_subscription_tier(
    data: ChangeTierRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member or member.role not in [RoleEnum.OWNER, RoleEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Admin or Owner role required to change subscription plans.",
        )

    tier_upper = data.tier.upper()
    if tier_upper not in SubscriptionTierEnum.__members__:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier '{data.tier}'. Must be one of: {list(SubscriptionTierEnum.__members__.keys())}",
        )

    target_tier = SubscriptionTierEnum[tier_upper]
    sub = await QuotaService.get_or_create_subscription(db, org_id)
    sub.tier = target_tier
    sub.status = SubscriptionStatusEnum.ACTIVE
    now = datetime.now(timezone.utc)
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=30)
    sub.cancel_at_period_end = False

    await db.commit()
    await db.refresh(sub)
    return SubscriptionResponse.model_validate(sub)
