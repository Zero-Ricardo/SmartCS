"""
数据库服务层
负责把聊天记录异步存入 PostgreSQL
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models import ChatSession, ChatMessage, MessageRole


class DBService:
    """数据库操作服务"""

    async def create_session(
        self,
        db: AsyncSession,
        guest_id: Optional[str] = None,
        user_id: Optional[str] = None,
        title: str = "新对话",
    ) -> ChatSession:
        """创建新会话"""
        session = ChatSession(
            guest_id=guest_id,
            user_id=user_id,
            title=title,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_session(
        self,
        db: AsyncSession,
        session_id: str,
    ) -> Optional[ChatSession]:
        """获取会话"""
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_sessions_by_guest(
        self,
        db: AsyncSession,
        guest_id: str,
    ) -> List[ChatSession]:
        """获取访客的所有会话"""
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.guest_id == guest_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_sessions_by_user(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> List[ChatSession]:
        """获取用户的所有会话"""
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def bind_guest_to_user(
        self,
        db: AsyncSession,
        guest_id: str,
        user_id: str,
    ) -> int:
        """
        将访客的会话过户给用户
        返回迁移的会话数量
        """
        # 查询未绑定的会话
        query = select(ChatSession).where(
            ChatSession.guest_id == guest_id,
            ChatSession.user_id.is_(None),
        )
        result = await db.execute(query)
        sessions = result.scalars().all()
        count = len(sessions)

        if count > 0:
            stmt = (
                update(ChatSession)
                .where(ChatSession.guest_id == guest_id)
                .where(ChatSession.user_id.is_(None))
                .values(user_id=user_id)
            )
            await db.execute(stmt)
            await db.commit()

        return count

    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: MessageRole,
        content: str,
        citations: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatMessage:
        """添加消息"""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def get_messages(
        self,
        db: AsyncSession,
        session_id: str,
        limit: int = 50,
    ) -> List[ChatMessage]:
        """获取会话的消息历史"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())


# 全局服务实例
db_service = DBService()
