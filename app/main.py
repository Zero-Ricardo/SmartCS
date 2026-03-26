import os

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

# 注册路由
app.include_router(chat_router)
app.include_router(knowledge_router)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": settings.app_name}
