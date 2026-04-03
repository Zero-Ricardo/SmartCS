from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class AdminRegisterRequest(BaseModel):
    """管理员注册请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    confirm_password: str = Field(..., min_length=6, description="确认密码")

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('两次密码不一致')
        return v


class AdminLoginRequest(BaseModel):
    """管理员登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"


class AdminMeResponse(BaseModel):
    """管理员信息响应"""
    id: str
    username: str
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


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    doc_ids: List[str] = Field(..., description="文档ID列表")


class BatchProcessResponse(BaseModel):
    """批量处理响应"""
    message: str
    processed_count: int
    skipped_count: int

