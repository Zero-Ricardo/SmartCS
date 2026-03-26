"""
聊天相关的 Pydantic 数据模型
用于规范 Java 端传来的 JSON 格式，以及流式响应��据包格式
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
    user_message_id: str = Field(..., description="前端生成的用户消息 ID")
    ai_message_id: str = Field(..., description="前端预分配的 AI 消息 ID")


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


class FeedbackRequest(BaseModel):
    """反馈请求"""
    message_id: str = Field(..., description="消息 ID（前端生成的 UUID）")
    feedback_type: str = Field(..., description="反馈类型: up 或 down")
    reason: Optional[str] = Field(None, description="反馈理由（可选）")


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


class FeedbackResponse(BaseModel):
    """反馈响应"""
    success: bool
    message: str


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    session_id: str
    role: str
    content: str
    citations: Optional[List[dict]] = None
    feedback: Optional[str] = None  # 当前消息的反馈状态
    created_at: str


# ====== SSE 流式数据包 ======

class SSEDataPacket(BaseModel):
    """SSE 数据包格式（用于文档说明）"""
    event: Optional[str] = "message"
    data: str
