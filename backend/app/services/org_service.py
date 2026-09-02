import re
import uuid
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.organization import Organization, OrganizationMember
from app.models.enums import RoleEnum, MembershipStatus
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, MemberAdd, MemberUpdateRole


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "org"


class OrganizationService:
    @staticmethod
    async def generate_unique_slug(db: AsyncSession, base_name: str) -> str:
        base_slug = slugify(base_name)
        slug = base_slug
        counter = 1
        while True:
            stmt = select(Organization).where(Organization.slug == slug)
            res = await db.execute(stmt)
            if not res.scalar_one_or_none():
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1

    @staticmethod
    async def create_organization(
        db: AsyncSession, user_id: str, data: OrganizationCreate
    ) -> Organization:
        if data.slug:
            slug = slugify(data.slug)
            stmt = select(Organization).where(Organization.slug == slug)
            res = await db.execute(stmt)
            if res.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization with this slug already exists.",
                )
        else:
            slug = await OrganizationService.generate_unique_slug(db, data.name)

        org = Organization(
            name=data.name.strip(),
            slug=slug,
        )
        db.add(org)
        await db.flush()

        # Add creator as OWNER
        member = OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            role=RoleEnum.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        db.add(member)
        await db.commit()
        await db.refresh(org)
        return org

    @staticmethod
    async def get_user_organizations(
        db: AsyncSession, user_id: str
    ) -> List[dict]:
        stmt = (
            select(Organization, OrganizationMember.role)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == user_id)
            .order_by(Organization.created_at.desc())
        )
        result = await db.execute(stmt)
        orgs = []
        for org, role in result.all():
            orgs.append({
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "role": role,
                "created_at": org.created_at,
                "updated_at": org.updated_at,
            })
        return orgs

    @staticmethod
    async def get_organization_by_id(
        db: AsyncSession, org_id: str
    ) -> Optional[Organization]:
        stmt = select(Organization).where(Organization.id == org_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_member(
        db: AsyncSession, org_id: str, user_id: str
    ) -> Optional[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == user_id,
                )
            )
            .options(selectinload(OrganizationMember.user))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_members(
        db: AsyncSession, org_id: str
    ) -> List[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org_id)
            .options(selectinload(OrganizationMember.user))
            .order_by(OrganizationMember.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_organization(
        db: AsyncSession, org_id: str, data: OrganizationUpdate
    ) -> Organization:
        org = await OrganizationService.get_organization_by_id(db, org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )
        if data.name is not None:
            org.name = data.name.strip()
        await db.commit()
        await db.refresh(org)
        return org

    @staticmethod
    async def add_member_by_email(
        db: AsyncSession, org_id: str, data: MemberAdd
    ) -> OrganizationMember:
        # Check target user
        stmt = select(User).where(User.email == data.email.lower().strip())
        res = await db.execute(stmt)
        target_user = res.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User with this email does not exist. Please have them register first.",
            )

        existing_member = await OrganizationService.get_member(db, org_id, target_user.id)
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization.",
            )

        member = OrganizationMember(
            organization_id=org_id,
            user_id=target_user.id,
            role=data.role,
            status=MembershipStatus.ACTIVE,
        )
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return await OrganizationService.get_member(db, org_id, target_user.id)  # returns with user loaded

    @staticmethod
    async def update_member_role(
        db: AsyncSession, org_id: str, target_user_id: str, data: MemberUpdateRole, current_user_id: str
    ) -> OrganizationMember:
        member = await OrganizationService.get_member(db, org_id, target_user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization.",
            )
        if member.role == RoleEnum.OWNER and data.role != RoleEnum.OWNER:
            # Check if there is another OWNER
            stmt = select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role == RoleEnum.OWNER,
                    OrganizationMember.user_id != target_user_id,
                )
            )
            owners = (await db.execute(stmt)).scalars().all()
            if not owners:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the sole OWNER from the organization.",
                )

        member.role = data.role
        await db.commit()
        await db.refresh(member)
        return member

    @staticmethod
    async def remove_member(
        db: AsyncSession, org_id: str, target_user_id: str, current_user_id: str
    ) -> None:
        member = await OrganizationService.get_member(db, org_id, target_user_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization.",
            )

        if member.role == RoleEnum.OWNER:
            stmt = select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.role == RoleEnum.OWNER,
                    OrganizationMember.user_id != target_user_id,
                )
            )
            owners = (await db.execute(stmt)).scalars().all()
            if not owners:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the only OWNER of an organization.",
                )

        await db.delete(member)
        await db.commit()
