from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    user = await AuthService.register_user(db, data)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and return JWT token",
)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    token_response = await AuthService.authenticate_user(db, data)
    return token_response


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get profile of the currently logged-in user",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update profile of the currently logged-in user",
)
async def update_current_user_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name.strip()
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout current user",
)
async def logout(
    current_user: User = Depends(get_current_user),
):
    return {"message": "Successfully logged out"}
