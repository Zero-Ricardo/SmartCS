"""
聊天 API 路由
只负责接客（接收请求、返回响应），不写 AI 逻辑
"""
import uuid
from datetime import datetime
from typing import Optional, List, AsyncGenerator
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.security import verify_internal_secret
from app.models import ChatSession, ChatMessage, ChatFeedback, MessageRole
from app.schemas.chat import (
    SessionResponse,
    BindRequest,
    BindResponse,
    ChatStreamRequest,
    MessageResponse,
    FeedbackRequest,
    FeedbackResponse,
)

router = APIRouter(
    prefix="/internal/chat",
    tags=["chat"],
    dependencies=[Depends(verify_internal_secret)],
)


# ====== Endpoints ======

@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    guest_id: Optional[str] = Query(None, description="访客 ID"),
    user_id: Optional[str] = Query(None, description="用户 ID"),
    db: AsyncSession = Depends(get_db),
):
    """查询会话列表"""
    query = select(ChatSession).order_by(ChatSession.updated_at.desc())

    if user_id:
        query = query.where(ChatSession.user_id == user_id)
    elif guest_id:
        query = query.where(ChatSession.guest_id == guest_id)
    else:
        return []

    result = await db.execute(query)
    sessions = result.scalars().all()

    return [
        SessionResponse(
            id=str(s.id),
            user_id=s.user_id,
            guest_id=s.guest_id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: str = Query(..., description="会话 ID"),
    db: AsyncSession = Depends(get_db),
):
    """查询会话的历史消息"""
    from app.services.db_service import db_service

    messages = await db_service.get_messages(db, session_id, limit=50)

    return [
        MessageResponse(
            id=str(m.id),
            session_id=str(m.session_id),
            role=m.role.value,
            content=m.content,
            citations=m.citations,
            feedback=m.feedback.feedback_type if m.feedback else None,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.post("/bind", response_model=BindResponse)
async def bind_guest_to_user(
    request: BindRequest,
    db: AsyncSession = Depends(get_db),
):
    """访客数据过户"""
    query = select(ChatSession).where(
        ChatSession.guest_id == request.guest_id,
        ChatSession.user_id.is_(None),
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    if not sessions:
        return BindResponse(
            success=True,
            migrated_sessions=0,
            message="没有需要迁移的会话",
        )

    stmt = (
        update(ChatSession)
        .where(ChatSession.guest_id == request.guest_id)
        .where(ChatSession.user_id.is_(None))
        .values(user_id=request.user_id)
    )
    await db.execute(stmt)
    await db.commit()

    return BindResponse(
        success=True,
        migrated_sessions=len(sessions),
        message=f"成功将 {len(sessions)} 个会话过户给用户 {request.user_id}",
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    提交消息反馈（有用/无用）

    - 仅支持 assistant 消息
    - feedback_type 只能是 "up" 或 "down"
    - 支持可选的 reason 字段
    """
    # 验证反馈类型
    if request.feedback_type not in ("up", "down"):
        return FeedbackResponse(success=False, message="无效的反馈类型")

    # 查找消息
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.id == request.message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        return FeedbackResponse(success=False, message="消息不存在")

    # 只有 assistant 消息才能反馈
    if message.role != MessageRole.ASSISTANT:
        return FeedbackResponse(success=False, message="只能对 AI 回复进行反馈")

    # 查找是否已有反馈记录
    existing_feedback = await db.execute(
        select(ChatFeedback).where(ChatFeedback.message_id == request.message_id)
    )
    feedback_record = existing_feedback.scalar_one_or_none()

    if feedback_record:
        # 更新已有反馈
        feedback_record.feedback_type = request.feedback_type
        feedback_record.reason = request.reason
    else:
        # 创建新反馈记录
        feedback_record = ChatFeedback(
            message_id=request.message_id,
            session_id=message.session_id,
            feedback_type=request.feedback_type,
            reason=request.reason,
        )
        db.add(feedback_record)

    await db.commit()

    return FeedbackResponse(success=True, message="反馈提交成功")


@router.post("/stream")
async def chat_stream(
    request: ChatStreamRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE 流式聊天接口（LangGraph Agent 版本）

    - 支持创建新会话或继续已有会话
    - 使用 LangGraph 进行意图识别 → 问题改写 → 检索 → 生成
    - 返回 SSE 多事件流：chunk（文本块）+ citations（引用）
    - 消息 ID 由前端生成，后端直接使用
    """
    from app.agent.graph import stream_agent
    from app.services.db_service import db_service

    # 确定会话 ID
    session_id = request.session_id

    if not session_id:
        session_id = str(uuid.uuid4())
        new_session = ChatSession(
            id=session_id,
            guest_id=request.guest_id,
            user_id=request.user_id,
            title=request.query[:50] if len(request.query) > 50 else request.query,
        )
        db.add(new_session)
        await db.commit()

    # 保存用户消息（使用前端传来的 ID）
    user_message = ChatMessage(
        id=request.user_message_id,
        session_id=session_id,
        role=MessageRole.USER,
        content=request.query,
    )
    db.add(user_message)
    await db.commit()

    # 查询历史消息（用于上下文）
    history_messages = []
    try:
        past_messages = await db_service.get_messages(db, session_id, limit=10)
        # 排除最后一条（刚保存的用户消息）
        for msg in past_messages[:-1]:
            role = "assistant" if msg.role == MessageRole.ASSISTANT else "user"
            history_messages.append({"role": role, "content": msg.content})
    except Exception:
        pass  # 历史消息非关键，出错则忽略

    async def agent_stream() -> AsyncGenerator[str, None]:
        """LangGraph Agent 流式输出"""
        full_response = ""
        citations = []

        # 首先输出 session_id 给前端
        import json
        yield f'event: session\ndata: {json.dumps({"session_id": session_id})}\n\n'

        async for event in stream_agent(
            query=request.query,
            session_id=session_id,
            history_messages=history_messages,
        ):
            if event["type"] == "chunk":
                # 累积完整回复
                full_response += event["content"]
                # 输出 SSE 格式
                yield f'data: {event["content"]}\n\n'
            elif event["type"] == "citations":
                citations = event["citations"]
                # 输出 citations 事件给前端
                import json
                yield f'event: citations\ndata: {json.dumps(event["citations"])}\n\n'
            elif event["type"] == "done":
                # 流结束，保存 AI 回复到数据库（使用前端预分配的 ID）
                if full_response:
                    assistant_message = ChatMessage(
                        id=request.ai_message_id,
                        session_id=session_id,
                        role=MessageRole.ASSISTANT,
                        content=full_response,
                        citations=citations if citations else None,
                    )
                    db.add(assistant_message)
                    await db.commit()

                # SSE 结束标记
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        agent_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
