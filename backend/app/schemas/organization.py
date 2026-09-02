from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.enums import RoleEnum, MembershipStatus
from app.schemas.auth import UserResponse


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)


class OrganizationCreate(OrganizationBase):
    slug: Optional[str] = Field(None, min_length=2, max_length=255)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    created_at: datetime
    updated_at: datetime


class UserInMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: Optional[str] = None


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    user_id: str
    role: RoleEnum
    status: MembershipStatus
    created_at: datetime
    user: Optional[UserInMember] = None


class MemberAdd(BaseModel):
    email: EmailStr
    role: RoleEnum = RoleEnum.VIEWER


class MemberUpdateRole(BaseModel):
    role: RoleEnum


class OrganizationWithRoleResponse(OrganizationResponse):
    role: RoleEnum
