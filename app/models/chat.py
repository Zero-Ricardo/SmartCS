import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
import enum

from app.core.database import Base


class MessageRole(str, enum.Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"


class FeedbackType(str, enum.Enum):
    """反馈类型枚举"""
    UP = "up"
    DOWN = "down"


class ChatSession(Base):
    """聊天会话表"""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    guest_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # 关联消息
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    # 关联反馈
    feedbacks: Mapped[List["ChatFeedback"]] = relationship(
        "ChatFeedback",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_chat_sessions_user_guest", "user_id", "guest_id"),
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.id}>"


class ChatMessage(Base):
    """聊天消息表"""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(
            MessageRole,
            values_callable=lambda x: [e.value for e in x],
            native=False,
            store_native=True,
        ),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联会话
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    # 关联反馈
    feedback: Mapped[Optional["ChatFeedback"]] = relationship(
        "ChatFeedback",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage {self.id} role={self.role}>"


class ChatFeedback(Base):
    """聊天反馈表（独立）"""
    __tablename__ = "chat_feedbacks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    feedback_type: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 关联消息
    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="feedback")

    # 关联会话
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="feedbacks")

    __table_args__ = (
        Index("ix_chat_feedbacks_type_created", "feedback_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatFeedback {self.id} type={self.feedback_type}>"
