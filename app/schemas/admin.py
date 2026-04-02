from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class AdminRegisterRequest(BaseModel):
    """管理员注册请求"""
    email: EmailStr = Field(..., description="电子邮箱")
    password: str = Field(..., min_length=6, description="密码")
    company_name: Optional[str] = Field(None, description="公司名称")


class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    email: EmailStr = Field(..., description="电子邮箱")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class AdminMeResponse(BaseModel):
    """管理员信息响应"""
    id: str
    email: str
    company_name: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """文档信息响应"""
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    ingest_progress: int
    chunk_count: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    total: int
    documents: list[DocumentResponse]

