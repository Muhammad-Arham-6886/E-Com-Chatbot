from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditLogService:
    @classmethod
    async def log_event(
        cls,
        db: AsyncSession,
        action: str,
        resource_type: str,
        org_id: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """
        Records an immutable audit event for security and compliance tracking.
        """
        log = AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @classmethod
    async def list_logs(
        cls,
        db: AsyncSession,
        org_id: str,
        page: int = 1,
        limit: int = 50,
        action: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[AuditLog], int]:
        """
        Retrieves paginated audit logs for an organization.
        """
        conditions = [AuditLog.organization_id == org_id]

        if action:
            conditions.append(AuditLog.action == action)

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                (AuditLog.action.ilike(search_pattern))
                | (AuditLog.resource_type.ilike(search_pattern))
                | (AuditLog.resource_id.ilike(search_pattern))
            )

        count_stmt = select(func.count(AuditLog.id)).where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar_one() or 0

        offset = (page - 1) * limit
        stmt = (
            select(AuditLog)
            .options(selectinload(AuditLog.user))
            .where(and_(*conditions))
            .order_by(desc(AuditLog.created_at))
            .offset(offset)
            .limit(limit)
        )
        logs = (await db.execute(stmt)).scalars().all()
        return list(logs), total
