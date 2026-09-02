from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_org_member
from app.models.enums import RoleEnum
from app.models.organization import OrganizationMember
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.organization import (
    MemberAdd,
    MemberResponse,
    MemberUpdateRole,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationWithRoleResponse,
)
from app.services.org_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations & Multi-Tenancy"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization (caller becomes OWNER)",
)
async def create_organization(
    data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await OrganizationService.create_organization(db, current_user.id, data)
    return org


@router.get(
    "",
    response_model=List[OrganizationWithRoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List all organizations the current user belongs to",
)
async def list_user_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orgs = await OrganizationService.get_user_organizations(db, current_user.id)
    return orgs


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific organization",
)
async def get_organization(
    org_id: str,
    member: OrganizationMember = Depends(require_org_member(RoleEnum.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    org = await OrganizationService.get_organization_by_id(db, org_id)
    return org


@router.put(
    "/{org_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update organization details (Requires ADMIN or OWNER)",
)
async def update_organization(
    org_id: str,
    data: OrganizationUpdate,
    member: OrganizationMember = Depends(require_org_member(RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    org = await OrganizationService.update_organization(db, org_id, data)
    return org


@router.get(
    "/{org_id}/members",
    response_model=List[MemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List all members in the organization",
)
async def list_members(
    org_id: str,
    member: OrganizationMember = Depends(require_org_member(RoleEnum.VIEWER)),
    db: AsyncSession = Depends(get_db),
):
    members = await OrganizationService.list_members(db, org_id)
    return members


@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add / invite a user to the organization (Requires ADMIN or OWNER)",
)
async def add_member(
    org_id: str,
    data: MemberAdd,
    member: OrganizationMember = Depends(require_org_member(RoleEnum.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    new_member = await OrganizationService.add_member_by_email(db, org_id, data)
    return new_member


@router.put(
    "/{org_id}/members/{user_id}",
    response_model=MemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a member's role (Requires OWNER or ADMIN)",
)
async def update_member_role(
    org_id: str,
    user_id: str,
    data: MemberUpdateRole,
    member: OrganizationMember = Depends(require_org_member(RoleEnum.ADMIN)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    updated = await OrganizationService.update_member_role(
        db, org_id, user_id, data, current_user.id
    )
    return updated


@router.delete(
    "/{org_id}/members/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a member from the organization (Requires OWNER or ADMIN)",
)
async def remove_member(
    org_id: str,
    user_id: str,
    member: OrganizationMember = Depends(require_org_member(RoleEnum.ADMIN)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await OrganizationService.remove_member(db, org_id, user_id, current_user.id)
    return {"message": "Member removed successfully"}
