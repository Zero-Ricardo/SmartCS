import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db, async_session_factory
from app.core.security import get_current_admin
from app.models.admin import AdminUser, KnowledgeDocument
from app.models.quota import AdminQuota
from app.schemas.admin import DocumentResponse, DocumentListResponse
from app.core.config import settings
from app.services.text_splitter import text_splitter
from app.services.qdrant_service import qdrant_service

router = APIRouter(
    prefix="/admin/knowledge",
    tags=["admin_knowledge"],
    dependencies=[Depends(get_current_admin)]
)


# ====== 后台入库任务 ======

def update_ingest_status(doc_id: str, current: int, total: int, status: str = "ingesting", error: str = None):
    """同步更新入库进度（在后台线程中调用）"""
    from sqlalchemy import create_engine, update as sa_update
    sync_url = settings.database_url.replace("postgresql+psycopg://", "postgresql+psycopg2://")
    engine = create_engine(sync_url)

    progress = int((current / total) * 100) if total > 0 else 0

    with engine.connect() as conn:
        stmt = sa_update(KnowledgeDocument).where(KnowledgeDocument.id == doc_id).values(
            status=status,
            ingest_progress=progress,
            error_message=error
        )
        if status == "ingested":
            stmt = stmt.values(chunk_count=total)
        conn.execute(stmt)
        conn.commit()
    engine.dispose()


async def process_ingest_task(doc_id: str):
    """后台任务：执行向量入库"""
    async with async_session_factory() as db:
        doc = await db.get(KnowledgeDocument, doc_id)
        if not doc or not doc.md_content:
            return

        try:
            # 1. 切分文本
            chunks = text_splitter.split_text(
                text=doc.md_content,
                source=doc.filename,
                doc_title=doc.filename.replace(".md", "")
            )

            if not chunks:
                doc.status = "failed"
                doc.error_message = "No valid chunks after splitting"
                await db.commit()
                return

            # 2. 向量化并入库（带进度回调）
            def progress_callback(current, total):
                update_ingest_status(doc_id, current, total)

            qdrant_service.add_documents(
                documents=chunks,
                doc_id=doc_id,
                progress_callback=progress_callback
            )

            # 3. 完成
            doc.status = "ingested"
            doc.ingest_progress = 100
            doc.chunk_count = len(chunks)
            await db.commit()

        except Exception as e:
            doc.status = "failed"
            doc.error_message = str(e)
            await db.commit()


# ====== API 路由 ======

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """上传知识库文档"""
    # 1. 校验配额
    quota_result = await db.execute(select(AdminQuota).where(AdminQuota.admin_user_id == current_admin.id))
    quota = quota_result.scalar_one_or_none()

    if quota:
        if quota.used_documents >= quota.max_documents:
            raise HTTPException(status_code=403, detail="Document count limit reached")

    # 2. 检查后缀
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".md", ".pdf", ".docx", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # 准备存储目录
    user_upload_dir = os.path.join(settings.upload_dir, str(current_admin.id))
    os.makedirs(user_upload_dir, exist_ok=True)

    # 生成存储文件名
    file_id = str(uuid.uuid4())
    storage_filename = f"{file_id}{ext}"
    storage_path = os.path.join(user_upload_dir, storage_filename)

    # 保存文件
    content = await file.read()
    file_size = len(content)

    with open(storage_path, "wb") as f:
        f.write(content)

    # 如果是 MD，提取内容
    md_content = None
    status = "uploaded"
    if ext == ".md":
        try:
            md_content = content.decode("utf-8")
            status = "parsed"
        except Exception:
            pass

    # 创建记录
    new_doc = KnowledgeDocument(
        admin_user_id=current_admin.id,
        filename=file.filename,
        file_type=ext[1:],
        file_size=file_size,
        storage_path=storage_path,
        md_content=md_content,
        status=status
    )

    db.add(new_doc)

    # 更新配额用量
    if quota:
        quota.used_documents += 1
        quota.used_file_storage_bytes += file_size

    await db.commit()
    await db.refresh(new_doc)

    return new_doc


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """获取文档列表"""
    count_query = select(func.count()).select_from(KnowledgeDocument).where(
        KnowledgeDocument.admin_user_id == current_admin.id
    )
    total = (await db.execute(count_query)).scalar()

    query = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.admin_user_id == current_admin.id)
        .order_by(KnowledgeDocument.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(total=total, documents=documents)


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document_detail(
    doc_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """获取单个文档详情"""
    query = select(KnowledgeDocument).where(
        KnowledgeDocument.id == doc_id,
        KnowledgeDocument.admin_user_id == current_admin.id
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return doc


@router.post("/documents/{doc_id}/ingest")
async def trigger_ingest(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """手动触发向量入库"""
    query = select(KnowledgeDocument).where(
        KnowledgeDocument.id == doc_id,
        KnowledgeDocument.admin_user_id == current_admin.id
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.md_content:
        raise HTTPException(status_code=400, detail="Document has no markdown content to ingest")

    if doc.status == "ingesting":
        raise HTTPException(status_code=400, detail="Already ingesting")

    # 更新状态为入库中
    doc.status = "ingesting"
    doc.ingest_progress = 0
    await db.commit()

    # 加入后台任务
    background_tasks.add_task(process_ingest_task, doc_id)

    return {"message": "Ingest task started"}


@router.delete("/documents/{doc_id}/vectors")
async def delete_vectors(
    doc_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """仅删除文档对应的向量"""
    query = select(KnowledgeDocument).where(
        KnowledgeDocument.id == doc_id,
        KnowledgeDocument.admin_user_id == current_admin.id
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    qdrant_service.delete_by_doc_id(doc_id)

    doc.status = "parsed" if doc.md_content else "uploaded"
    doc.ingest_progress = 0
    doc.chunk_count = 0
    await db.commit()

    return {"message": "Vectors deleted successfully"}


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """彻底删除文档（文件+向量+记录）"""
    query = select(KnowledgeDocument).where(
        KnowledgeDocument.id == doc_id,
        KnowledgeDocument.admin_user_id == current_admin.id
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 获取配额
    quota_result = await db.execute(select(AdminQuota).where(AdminQuota.admin_user_id == current_admin.id))
    quota = quota_result.scalar_one_or_none()
    file_size = doc.file_size
    chunk_count = doc.chunk_count

    # 1. 删向量
    qdrant_service.delete_by_doc_id(doc_id)

    # 2. 删物理文件
    if doc.storage_path and os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
        except OSError:
            pass

    # 3. 删数据库记录
    await db.delete(doc)

    # 4. 更新配额
    if quota:
        quota.used_documents = max(0, quota.used_documents - 1)
        quota.used_file_storage_bytes = max(0, quota.used_file_storage_bytes - file_size)
        quota.used_vector_points = max(0, quota.used_vector_points - chunk_count)

    await db.commit()

    return {"message": "Document deleted successfully"}
