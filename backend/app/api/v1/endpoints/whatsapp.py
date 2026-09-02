from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import RoleEnum
from app.models.user import User
from app.models.website import Website
from app.schemas.whatsapp import WhatsAppPreviewRequest, WhatsAppPreviewResponse
from app.services.org_service import OrganizationService
from app.services.whatsapp_service import WhatsAppHandoffService

router = APIRouter(tags=["WhatsApp Human Handoff Bridge"])


@router.post(
    "/websites/{website_id}/whatsapp-preview",
    response_model=WhatsAppPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate live WhatsApp click-to-chat deep link and message preview",
)
async def preview_whatsapp_handoff(
    website_id: str,
    data: WhatsAppPreviewRequest,
    org_id: str = Query(..., description="Organization UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of this organization.",
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

    clean_phone = WhatsAppHandoffService.normalize_phone_number(data.phone_number)
    is_valid = len(clean_phone) >= 7

    formatted_message = WhatsAppHandoffService.format_message_template(
        template=data.custom_template,
        store_name=website.name,
        visitor_id=data.visitor_id or "visitor_preview",
        session_id="preview_sess_891",
        last_inquiry=data.sample_inquiry or "Warranty & shipping question",
    )

    preview_url = WhatsAppHandoffService.build_handoff_url(
        raw_phone=clean_phone,
        message_text=formatted_message,
    )

    return WhatsAppPreviewResponse(
        is_valid_phone=is_valid,
        clean_phone=clean_phone,
        formatted_message=formatted_message,
        preview_url=preview_url,
    )
