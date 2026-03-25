"""
知识库 API 路由
"""
from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_internal_secret
from app.schemas.chat import (
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeDocument,
)
from app.services.qdrant_service import qdrant_service
from app.services.text_splitter import text_splitter

router = APIRouter(
    prefix="/internal/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(verify_internal_secret)],
)


def ingest_documents_task(documents: List[KnowledgeDocument]):
    """后台任务：处理文档导入"""
    all_chunk_docs = []

    for doc in documents:
        # 使用语义切分器切分文档
        chunk_docs = text_splitter.split_text(
            text=doc.content,
            source=doc.source,
            doc_title=doc.doc_title,
        )
        all_chunk_docs.extend(chunk_docs)

    if all_chunk_docs:
        qdrant_service.add_documents(all_chunk_docs)


@router.post("/ingest", response_model=KnowledgeIngestResponse)
async def ingest_knowledge(
    request: KnowledgeIngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    知识库导入接口（异步）

    - 接收 Markdown 文档列表
    - 后台异步处理：语义切分 → 向量化 → 存入 Qdrant
    - 立即返回，不阻塞
    """
    if not request.documents:
        return KnowledgeIngestResponse(
            success=False,
            ingested_chunks=0,
            message="没有需要导入的文档",
        )

    # 添加后台任务
    background_tasks.add_task(
        ingest_documents_task,
        request.documents,
    )

    doc_count = len(request.documents)
    return KnowledgeIngestResponse(
        success=True,
        ingested_chunks=0,  # 异步处理，暂时返回 0
        message=f"已接收 {doc_count} 个文档，正在后台处理",
    )


@router.post("/ingest/sync", response_model=KnowledgeIngestResponse)
async def ingest_knowledge_sync(
    request: KnowledgeIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    知识库同步导入接口

    - 同步处理，等待完成后返回
    - 适合小批量测试
    - 返回实际导入的 chunk 数量
    """
    if not request.documents:
        return KnowledgeIngestResponse(
            success=False,
            ingested_chunks=0,
            message="没有需要导入的文档",
        )

    try:
        all_chunk_docs = []

        for doc in request.documents:
            # 使用语义切分器切分文档
            chunk_docs = text_splitter.split_text(
                text=doc.content,
                source=doc.source,
                doc_title=doc.doc_title,
            )
            all_chunk_docs.extend(chunk_docs)

        if not all_chunk_docs:
            return KnowledgeIngestResponse(
                success=False,
                ingested_chunks=0,
                message="切分后没有有效的文本块",
            )

        # 向量化并存储
        ids = qdrant_service.add_documents(all_chunk_docs)

        return KnowledgeIngestResponse(
            success=True,
            ingested_chunks=len(ids),
            message=f"成功导入 {len(ids)} 个文本块（来自 {len(request.documents)} 个文档）",
        )
    except Exception as e:
        return KnowledgeIngestResponse(
            success=False,
            ingested_chunks=0,
            message=f"导入失败: {str(e)}",
        )
