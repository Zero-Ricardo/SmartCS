from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_admin
)
from app.models.admin import AdminUser
from app.schemas.admin import (
    AdminRegisterRequest,
    AdminLoginRequest,
    TokenResponse,
    AdminMeResponse
)
from app.core.config import settings

from app.models.quota import AdminQuota

router = APIRouter(
    prefix="/admin",
    tags=["admin_auth"],
)


@router.post("/register", response_model=AdminMeResponse)
async def register(request: AdminRegisterRequest, db: AsyncSession = Depends(get_db)):
    """管理员注册"""
    # 检查邮箱是否已存在
    result = await db.execute(select(AdminUser).where(AdminUser.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_admin = AdminUser(
        email=request.email,
        password_hash=get_password_hash(request.password),
        company_name=request.company_name
    )

    # 为新用户创建默认配额
    new_quota = AdminQuota(admin_user=new_admin)
    db.add(new_admin)
    db.add(new_quota)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin


@router.post("/login", response_model=TokenResponse)
async def login(request: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    """管理员登录"""
    result = await db.execute(select(AdminUser).where(AdminUser.email == request.email))
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(request.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": admin.id})
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=AdminMeResponse)
async def get_me(current_admin: AdminUser = Depends(get_current_admin)):
    """获取当前用户信息"""
    return current_admin
