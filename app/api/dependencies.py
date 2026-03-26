"""
FastAPI 依赖注入
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

# Bearer Token 认证（可选，目前只用 X-Internal-Secret）
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    从 Bearer Token 中解析用户 ID（可选）

    当前系统不负责 JWT 验证，由 Java 网关处理。
    此依赖预留用于未来可能的扩展。
    """
    if credentials:
        # 预留：如果将来需要从 token 解析 user_id
        pass
    return None


# 数据库会话依赖（直接导出）
get_db_session = get_db
