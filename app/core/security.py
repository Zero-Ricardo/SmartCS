from fastapi import Header, HTTPException, status
from typing import Optional

from app.core.config import settings


async def verify_internal_secret(
    x_internal_secret: Optional[str] = Header(None, alias="X-Internal-Secret")
) -> str:
    """
    服务间鉴权依赖

    校验请求头中的 X-Internal-Secret 是否与配置的密钥匹配。
    用于验证来自 Java 网关的内部请求。

    Raises:
        HTTPException: 401 未提供密钥或密钥无效
    """
    if x_internal_secret is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Internal-Secret header",
        )

    if x_internal_secret != settings.internal_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid X-Internal-Secret",
        )

    return x_internal_secret
