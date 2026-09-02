from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.security import (
    AuditLogResponse,
    PaginatedAuditLogsResponse,
    GuardrailTestRequest,
    GuardrailTestResponse,
)
from app.services.audit_service import AuditLogService
from app.services.org_service import OrganizationService
from app.services.security_guardrails import SecurityGuardrailsEngine

router = APIRouter(prefix="/security", tags=["Platform Security & Guardrails"])


@router.get(
    "/audit-logs",
    response_model=PaginatedAuditLogsResponse,
    summary="Get paginated audit logs for organization (Admin+)",
)
async def get_organization_audit_logs(
    org_id: str = Query(..., description="Organization UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action code"),
    search: Optional[str] = Query(None, description="Search keyword in action/resource"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await OrganizationService.get_member(db, org_id, current_user.id)
    if not member or member.role not in [RoleEnum.OWNER, RoleEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Admin or Owner role required to access security audit logs.",
        )

    logs, total = await AuditLogService.list_logs(
        db,
        org_id=org_id,
        page=page,
        limit=limit,
        action=action,
        search=search,
    )

    items = [AuditLogResponse.model_validate(log) for log in logs]
    return PaginatedAuditLogsResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.post(
    "/test-guardrails",
    response_model=GuardrailTestResponse,
    summary="Security playground to test prompt injection detection and PII redaction",
)
async def test_guardrails(
    data: GuardrailTestRequest,
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

    redacted, is_injection, reason = SecurityGuardrailsEngine.process_and_inspect_input(data.text)
    sanitized = SecurityGuardrailsEngine.sanitize_output(data.text)

    return GuardrailTestResponse(
        original_text=data.text,
        redacted_text=redacted,
        is_prompt_injection=is_injection,
        injection_reason=reason,
        sanitized_output_preview=sanitized,
    )
