"""
聊天相关的 Pydantic 数据模型
用于规范 Java 端传来的 JSON 格式，以及流式响应��数据包格式
"""
from typing import Optional, List
from pydantic import BaseModel, Field


# ====== 请求模型 ======

class ChatStreamRequest(BaseModel):
    """流式聊天请求"""
    guest_id: Optional[str] = Field(None, description="访客 ID")
    user_id: Optional[str] = Field(None, description="用户 ID")
    query: str = Field(..., description="用户问题")
    session_id: Optional[str] = Field(None, description="会话 ID（可选，不传则新建）")


class BindRequest(BaseModel):
    """访客数据过户请求"""
    guest_id: str = Field(..., description="访客 ID")
    user_id: str = Field(..., description="正式用户 ID")


class KnowledgeDocument(BaseModel):
    """单个知识库文档"""
    content: str = Field(..., description="Markdown 文档内容")
    source: str = Field(default="", description="原文链接")
    doc_title: str = Field(default="", description="文档标题")


class KnowledgeIngestRequest(BaseModel):
    """知识库导入请求"""
    documents: List[KnowledgeDocument] = Field(..., description="文档列表")


# ====== 响应模型 ======

class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: Optional[str] = None
    guest_id: Optional[str] = None
    title: str
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class BindResponse(BaseModel):
    """过户响应"""
    success: bool
    migrated_sessions: int
    message: str


class KnowledgeIngestResponse(BaseModel):
    """知识库导入响应"""
    success: bool
    ingested_chunks: int
    message: str


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    session_id: str
    role: str
    content: str
    citations: Optional[List[dict]] = None
    created_at: str


# ====== SSE 流式数据包 ======

class SSEDataPacket(BaseModel):
    """SSE 数据包格式（用于文档说明）"""
    event: Optional[str] = "message"
    data: str
