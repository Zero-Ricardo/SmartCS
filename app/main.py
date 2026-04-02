import os
import sys
import asyncio

# 针对 Windows 系统的异步事件循环修复
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 禁用代理（必须在导入其他模块前设置）
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.chat import router as chat_router
from app.api.knowledge import router as knowledge_router
from app.api.admin_auth import router as admin_auth_router
from app.api.admin_knowledge import router as admin_knowledge_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description="内部 AI 微服务引擎，提供 RAG 问答与会话管理",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置（内网服务，限制来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（统一 /api 前缀）
app.include_router(chat_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(admin_auth_router, prefix="/api")
app.include_router(admin_knowledge_router, prefix="/api")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": settings.app_name}
