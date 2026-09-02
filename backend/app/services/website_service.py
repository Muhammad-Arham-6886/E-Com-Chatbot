import secrets
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.website import Website, WebsiteSettings, WebsiteDomain
from app.models.enums import PlatformEnum, WebsiteStatusEnum
from app.schemas.website import (
    WebsiteCreate,
    WebsiteUpdate,
    WebsiteSettingsUpdate,
    PublicWidgetConfigResponse,
    PlatformDetectionResponse,
)
from app.services.platform_detector import PlatformDetector


class WebsiteService:
    @staticmethod
    def generate_public_site_id() -> str:
        """Generates a secure, unique public site identifier for the widget embed."""
        random_suffix = secrets.token_hex(12)  # 24 chars
        return f"site_{random_suffix}"

    @staticmethod
    async def create_website(
        db: AsyncSession, org_id: str, data: WebsiteCreate
    ) -> Website:
        try:
            normalized_url, domain = PlatformDetector.normalize_url(data.url)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # Check if website with same URL/domain already exists in this organization
        stmt = select(Website).where(
            and_(
                Website.organization_id == org_id,
                Website.domain == domain,
            )
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A website with domain '{domain}' already exists in your organization.",
            )

        public_site_id = WebsiteService.generate_public_site_id()

        website = Website(
            organization_id=org_id,
            name=data.name.strip(),
            url=normalized_url,
            domain=domain,
            public_site_id=public_site_id,
            platform=PlatformEnum.UNKNOWN,
            status=WebsiteStatusEnum.ACTIVE,
        )
        db.add(website)
        await db.flush()

        # Create default WebsiteSettings
        settings = WebsiteSettings(
            website_id=website.id,
            chatbot_name=f"{website.name} Assistant",
            welcome_message=f"Hi there! How can I help you on {website.name} today?",
            placeholder_text="Ask anything...",
            primary_color="#4F46E5",
            secondary_color="#1E1B4B",
            launcher_position="bottom-right",
            widget_size="medium",
            border_radius="16px",
            enable_whatsapp=False,
        )
        db.add(settings)

        # Create default Primary WebsiteDomain
        domain_entry = WebsiteDomain(
            website_id=website.id,
            domain=domain,
            is_primary=True,
            is_verified=True,
        )
        db.add(domain_entry)

        await db.commit()
        await db.refresh(website)

        # Fetch with relationships loaded
        return await WebsiteService.get_website(db, website.id, org_id)

    @staticmethod
    async def list_websites(
        db: AsyncSession, org_id: str
    ) -> List[Website]:
        stmt = (
            select(Website)
            .where(Website.organization_id == org_id)
            .order_by(Website.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_website(
        db: AsyncSession, website_id: str, org_id: Optional[str] = None
    ) -> Website:
        conditions = [Website.id == website_id]
        if org_id is not None:
            conditions.append(Website.organization_id == org_id)

        stmt = (
            select(Website)
            .where(and_(*conditions))
            .options(
                selectinload(Website.settings),
                selectinload(Website.domains),
            )
        )
        result = await db.execute(stmt)
        website = result.scalar_one_or_none()
        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Website not found or does not belong to your organization.",
            )
        return website

    @staticmethod
    async def update_website(
        db: AsyncSession, website_id: str, org_id: str, data: WebsiteUpdate
    ) -> Website:
        website = await WebsiteService.get_website(db, website_id, org_id)

        if data.name is not None:
            website.name = data.name.strip()
        if data.status is not None:
            website.status = data.status
        if data.platform is not None:
            website.platform = data.platform
        if data.url is not None:
            try:
                norm_url, domain = PlatformDetector.normalize_url(data.url)
                website.url = norm_url
                website.domain = domain
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

        await db.commit()
        await db.refresh(website)
        return website

    @staticmethod
    async def delete_website(
        db: AsyncSession, website_id: str, org_id: str
    ) -> None:
        website = await WebsiteService.get_website(db, website_id, org_id)
        await db.delete(website)
        await db.commit()

    @staticmethod
    async def update_settings(
        db: AsyncSession, website_id: str, org_id: str, data: WebsiteSettingsUpdate
    ) -> WebsiteSettings:
        website = await WebsiteService.get_website(db, website_id, org_id)
        settings = website.settings
        if not settings:
            settings = WebsiteSettings(website_id=website.id)
            db.add(settings)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

        await db.commit()
        await db.refresh(settings)
        return settings

    @staticmethod
    async def detect_website_platform(
        db: AsyncSession, website_id: str, org_id: str
    ) -> PlatformDetectionResponse:
        website = await WebsiteService.get_website(db, website_id, org_id)
        platform, confidence, signals = await PlatformDetector.detect_platform(website.url)

        website.platform = platform
        await db.commit()
        await db.refresh(website)

        return PlatformDetectionResponse(
            website_id=website.id,
            detected_platform=platform,
            confidence=confidence,
            detection_signals=signals,
        )

    @staticmethod
    async def get_public_config(
        db: AsyncSession, public_site_id: str
    ) -> PublicWidgetConfigResponse:
        from app.core.config import settings as app_settings

        stmt = (
            select(Website)
            .where(
                and_(
                    Website.public_site_id == public_site_id,
                    Website.status == WebsiteStatusEnum.ACTIVE,
                )
            )
            .options(selectinload(Website.settings))
        )
        result = await db.execute(stmt)
        website = result.scalar_one_or_none()
        if not website:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active widget configuration not found for this site identifier.",
            )

        settings = website.settings
        return PublicWidgetConfigResponse(
            website_id=website.id,
            public_site_id=website.public_site_id,
            website_name=website.name,
            chatbot_name=settings.chatbot_name if settings else "AI Assistant",
            welcome_message=settings.welcome_message if settings else "Hi there! How can I help you today?",
            placeholder_text=settings.placeholder_text if settings else "Ask anything...",
            primary_color=settings.primary_color if settings else "#4F46E5",
            secondary_color=settings.secondary_color if settings else "#1E1B4B",
            launcher_position=settings.launcher_position if settings else "bottom-right",
            widget_size=settings.widget_size if settings else "medium",
            border_radius=settings.border_radius if settings else "16px",
            enable_whatsapp=settings.enable_whatsapp if settings else False,
            whatsapp_number=settings.whatsapp_number if settings else None,
            whatsapp_custom_message=settings.whatsapp_custom_message if settings else None,
            whatsapp_handoff_trigger=settings.whatsapp_handoff_trigger if settings else "ON_ESCALATION",
            api_base_url=app_settings.WIDGET_BASE_URL,
        )
