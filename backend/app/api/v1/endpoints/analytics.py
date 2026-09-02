from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    AnalyticsTimeseriesResponse,
    IntentAnalyticsResponse,
    ConversionFunnelResponse,
    AnalyticsTimeseriesPoint,
    IntentDistributionItem,
    FunnelStageItem,
)
from app.services.analytics_service import AnalyticsService
from app.services.org_service import OrganizationService

router = APIRouter(prefix="/analytics", tags=["Analytics & Conversation Insights"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get high-level conversation, containment, and conversion KPIs",
)
async def get_analytics_overview(
    org_id: str = Query(..., description="Organization UUID"),
    website_id: Optional[str] = Query(None, description="Filter by website UUID"),
    period: str = Query("30d", description="Time window: 7d, 30d, 90d, all"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. You are not a member of this organization.",
        )

    kpis = await AnalyticsService.get_overview_kpis(
        db, org_id=org_id, website_id=website_id, period=period
    )
    return AnalyticsOverviewResponse(**kpis)


@router.get(
    "/timeseries",
    response_model=AnalyticsTimeseriesResponse,
    summary="Get daily conversation, message, and conversion time-series data",
)
async def get_analytics_timeseries(
    org_id: str = Query(..., description="Organization UUID"),
    website_id: Optional[str] = Query(None, description="Filter by website UUID"),
    period: str = Query("30d", description="Time window: 7d, 30d, 90d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. You are not a member of this organization.",
        )

    points_data = await AnalyticsService.get_timeseries_data(
        db, org_id=org_id, website_id=website_id, period=period
    )
    points = [AnalyticsTimeseriesPoint(**p) for p in points_data]
    return AnalyticsTimeseriesResponse(points=points)


@router.get(
    "/intents",
    response_model=IntentAnalyticsResponse,
    summary="Get breakdown of customer inquiry intents and topics",
)
async def get_intent_analytics(
    org_id: str = Query(..., description="Organization UUID"),
    website_id: Optional[str] = Query(None, description="Filter by website UUID"),
    period: str = Query("30d", description="Time window: 7d, 30d, 90d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. You are not a member of this organization.",
        )

    intents_data = await AnalyticsService.get_intent_distribution(
        db, org_id=org_id, website_id=website_id, period=period
    )
    intents = [IntentDistributionItem(**i) for i in intents_data]
    return IntentAnalyticsResponse(intents=intents)


@router.get(
    "/conversions",
    response_model=ConversionFunnelResponse,
    summary="Get step-by-step commerce conversion funnel data",
)
async def get_conversion_funnel(
    org_id: str = Query(..., description="Organization UUID"),
    website_id: Optional[str] = Query(None, description="Filter by website UUID"),
    period: str = Query("30d", description="Time window: 7d, 30d, 90d"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden. You are not a member of this organization.",
        )

    funnel_data = await AnalyticsService.get_conversion_funnel(
        db, org_id=org_id, website_id=website_id, period=period
    )
    stages = [FunnelStageItem(**s) for s in funnel_data["stages"]]
    return ConversionFunnelResponse(period=funnel_data["period"], stages=stages)
