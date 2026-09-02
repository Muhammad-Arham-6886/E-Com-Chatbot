from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import (
    OrganizationSubscription,
    OrganizationUsage,
    SubscriptionTierEnum,
    SubscriptionStatusEnum,
)
from app.models.website import Website
from app.models.chunk import DocumentChunk


TIER_LIMITS: Dict[SubscriptionTierEnum, Dict[str, Any]] = {
    SubscriptionTierEnum.FREE: {
        "name": "Free Sandbox",
        "price_monthly": 0,
        "max_websites": 1,
        "max_pages_per_crawl": 50,
        "max_chunks": 100,
        "max_monthly_messages": 200,
        "rate_limit_rpm": 60,
        "features": [
            "1 Website Connection",
            "50 Crawled Pages / Site",
            "100 Vector Chunks",
            "200 Monthly AI Chat Messages",
            "Standard Community Support",
        ],
    },
    SubscriptionTierEnum.STARTER: {
        "name": "Starter Pro",
        "price_monthly": 29,
        "max_websites": 3,
        "max_pages_per_crawl": 500,
        "max_chunks": 2000,
        "max_monthly_messages": 2000,
        "rate_limit_rpm": 120,
        "features": [
            "3 Website Connections",
            "500 Crawled Pages / Site",
            "2,000 Vector Chunks",
            "2,000 Monthly AI Chat Messages",
            "WooCommerce REST Integration",
            "Priority Email Support",
        ],
    },
    SubscriptionTierEnum.GROWTH: {
        "name": "Growth Business",
        "price_monthly": 79,
        "max_websites": 10,
        "max_pages_per_crawl": 2500,
        "max_chunks": 10000,
        "max_monthly_messages": 10000,
        "rate_limit_rpm": 300,
        "features": [
            "10 Website Connections",
            "2,500 Crawled Pages / Site",
            "10,000 Vector Chunks",
            "10,000 Monthly AI Chat Messages",
            "WhatsApp Bridge & Agent Takeover",
            "Custom System Prompts",
            "Dedicated Slack / Priority Support",
        ],
    },
    SubscriptionTierEnum.ENTERPRISE: {
        "name": "Enterprise Scale",
        "price_monthly": 299,
        "max_websites": 999999,
        "max_pages_per_crawl": 999999,
        "max_chunks": 999999,
        "max_monthly_messages": 999999,
        "rate_limit_rpm": 1000,
        "features": [
            "Unlimited Websites",
            "Unlimited Crawled Pages",
            "Unlimited Vector Chunks",
            "Unlimited AI Chat Messages",
            "Custom LLM Fine-Tuning & Deployments",
            "99.99% SLA & Dedicated Account Manager",
        ],
    },
}


class QuotaService:
    @staticmethod
    def get_current_period_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    @classmethod
    async def get_or_create_subscription(
        cls, db: AsyncSession, org_id: str
    ) -> OrganizationSubscription:
        stmt = select(OrganizationSubscription).where(
            OrganizationSubscription.organization_id == org_id
        )
        sub = (await db.execute(stmt)).scalar_one_or_none()
        if not sub:
            now = datetime.now(timezone.utc)
            sub = OrganizationSubscription(
                organization_id=org_id,
                tier=SubscriptionTierEnum.FREE,
                status=SubscriptionStatusEnum.ACTIVE,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                cancel_at_period_end=False,
            )
            db.add(sub)
            await db.flush()
        return sub

    @classmethod
    async def get_or_create_usage(
        cls, db: AsyncSession, org_id: str, period: Optional[str] = None
    ) -> OrganizationUsage:
        billing_period = period or cls.get_current_period_str()
        stmt = select(OrganizationUsage).where(
            and_(
                OrganizationUsage.organization_id == org_id,
                OrganizationUsage.billing_period == billing_period,
            )
        )
        usage = (await db.execute(stmt)).scalar_one_or_none()
        if not usage:
            usage = OrganizationUsage(
                organization_id=org_id,
                billing_period=billing_period,
                chat_messages_count=0,
                crawl_pages_count=0,
                vector_chunks_count=0,
                tokens_consumed=0,
                last_reset_at=datetime.now(timezone.utc),
            )
            db.add(usage)
            await db.flush()
        return usage

    @classmethod
    async def check_website_creation_allowed(cls, db: AsyncSession, org_id: str):
        sub = await cls.get_or_create_subscription(db, org_id)
        limits = TIER_LIMITS[sub.tier]

        count_stmt = select(func.count(Website.id)).where(Website.organization_id == org_id)
        current_websites_count = (await db.execute(count_stmt)).scalar_one() or 0

        if current_websites_count >= limits["max_websites"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Website limit ({limits['max_websites']}) reached for '{sub.tier.value}' plan. "
                    "Please upgrade your subscription to connect additional websites."
                ),
            )

    @classmethod
    async def clamp_crawl_pages_limit(
        cls, db: AsyncSession, org_id: str, requested_pages: int
    ) -> int:
        sub = await cls.get_or_create_subscription(db, org_id)
        limits = TIER_LIMITS[sub.tier]
        allowed_max = limits["max_pages_per_crawl"]
        return min(requested_pages, allowed_max)

    @classmethod
    async def check_chunk_limit(
        cls, db: AsyncSession, org_id: str, new_chunks_count: int = 1
    ):
        sub = await cls.get_or_create_subscription(db, org_id)
        limits = TIER_LIMITS[sub.tier]

        count_stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.organization_id == org_id
        )
        current_chunks = (await db.execute(count_stmt)).scalar_one() or 0

        if (current_chunks + new_chunks_count) > limits["max_chunks"]:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"Vector chunk quota ({limits['max_chunks']}) exceeded for '{sub.tier.value}' plan. "
                    "Upgrade your subscription to index more knowledge documents."
                ),
            )

    @classmethod
    async def check_monthly_chat_quota(cls, db: AsyncSession, org_id: str) -> bool:
        sub = await cls.get_or_create_subscription(db, org_id)
        limits = TIER_LIMITS[sub.tier]
        usage = await cls.get_or_create_usage(db, org_id)
        return usage.chat_messages_count < limits["max_monthly_messages"]

    @classmethod
    async def increment_chat_usage(
        cls, db: AsyncSession, org_id: str, tokens: int = 0
    ):
        usage = await cls.get_or_create_usage(db, org_id)
        usage.chat_messages_count += 1
        usage.tokens_consumed += tokens
        await db.flush()

    @classmethod
    async def get_usage_breakdown(cls, db: AsyncSession, org_id: str) -> Dict[str, Any]:
        sub = await cls.get_or_create_subscription(db, org_id)
        limits = TIER_LIMITS[sub.tier]
        usage = await cls.get_or_create_usage(db, org_id)

        site_count_stmt = select(func.count(Website.id)).where(Website.organization_id == org_id)
        websites_used = (await db.execute(site_count_stmt)).scalar_one() or 0

        chunk_count_stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.organization_id == org_id
        )
        chunks_used = (await db.execute(chunk_count_stmt)).scalar_one() or 0

        messages_used = usage.chat_messages_count
        tokens_used = usage.tokens_consumed

        def calc_pct(used: int, max_val: int) -> float:
            if max_val >= 999999:
                return 0.0
            return round(min(100.0, (used / max_val) * 100), 1)

        return {
            "tier": sub.tier.value,
            "tier_name": limits["name"],
            "price_monthly": limits["price_monthly"],
            "status": sub.status.value,
            "billing_period": usage.billing_period,
            "period_end": sub.current_period_end,
            "websites": {
                "used": websites_used,
                "limit": limits["max_websites"],
                "percentage": calc_pct(websites_used, limits["max_websites"]),
            },
            "chat_messages": {
                "used": messages_used,
                "limit": limits["max_monthly_messages"],
                "percentage": calc_pct(messages_used, limits["max_monthly_messages"]),
            },
            "vector_chunks": {
                "used": chunks_used,
                "limit": limits["max_chunks"],
                "percentage": calc_pct(chunks_used, limits["max_chunks"]),
            },
            "tokens_consumed": tokens_used,
        }
