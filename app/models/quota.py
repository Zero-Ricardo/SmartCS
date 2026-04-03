import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, BIGINT, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AdminQuota(Base):
    """管理员存储配额表"""
    __tablename__ = "admin_quotas"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    admin_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # 配额限制（字节或数量）
    max_file_storage_bytes: Mapped[int] = mapped_column(BIGINT, default=1024*1024*1024)  # 默认 1GB
    max_vector_points: Mapped[int] = mapped_column(Integer, default=50000)                # 默认 5W 点
    max_documents: Mapped[int] = mapped_column(Integer, default=100)                     # 默认 100 篇

    # 已使用量
    used_file_storage_bytes: Mapped[int] = mapped_column(BIGINT, default=0)
    used_vector_points: Mapped[int] = mapped_column(Integer, default=0)
    used_documents: Mapped[int] = mapped_column(Integer, default=0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # 关联管理员
    admin_user: Mapped["AdminUser"] = relationship("AdminUser", back_populates="quota")

    def __repr__(self) -> str:
        return f"<AdminQuota for {self.admin_user_id}>"
