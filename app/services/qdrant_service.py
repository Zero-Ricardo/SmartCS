"""
Qdrant 向量数据库服务
支持 Dense + Sparse 混合检索（Hybrid Search）

核心概念：
- Dense Vector（稠密向量）：语义理解，由 Embedding 模型生成
- Sparse Vector（稀疏向量）：关键词匹配（BM25），由 fastembed 生成

入库时：每个 Chunk 生成两个向量，一起存入 Qdrant
检索时：同时传入两个查询向量，Qdrant 内部自动融合
"""
import os
import uuid
from typing import List, Optional, Dict, Any

# 强制让发往本机的网络请求不经过代理（解决 VPN 导致的 502 问题）
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"
os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"

from qdrant_client import QdrantClient
from qdrant_client import models
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PayloadSchemaType,
    SparseVector,
    QueryResponse,
)
from openai import OpenAI, AsyncOpenAI
from langchain_core.documents import Document

from app.core.config import settings

# 尝试导入 fastembed 稀疏向量模型
try:
    from fastembed import SparseTextEmbedding
    SPARSE_MODEL_NAME = "Qdrant/bm25"
    _sparse_model = None  # 延迟初始化
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False
    print("Warning: fastembed not available, hybrid search will be disabled")


# 需要创建索引的 metadata 字段
INDEXED_FIELDS = [
    "metadata.type",         # normal / image_description
    "metadata.source",       # 原文链接
    "metadata.doc_title",    # 文档标题
    "metadata.H1",
    "metadata.H2",
    "metadata.H3",
    "metadata.H4",
    "metadata.H5",
    "metadata.H6",
    "doc_id",
]


def get_sparse_model():
    """延迟初始化 sparse 模型（避免启动时加载）"""
    global _sparse_model
    if _sparse_model is None and FASTEMBED_AVAILABLE:
        from fastembed import SparseTextEmbedding
        _sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)
    return _sparse_model


class QdrantService:
    """Qdrant 向量数据库服务（支持混合检索）"""

    # 向量维度配置
    DENSE_VECTOR_SIZE = 1024  # text-embedding-v3 维度
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(self):
        # 只保留 NO_PROXY，确保 Qdrant 本地连接不走代理
        # 不要清空 HTTP_PROXY，否则会导致阿里云 API 连接超时！
        os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"

        self.qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        # 同步客户端（兼容旧代码）
        self.openai_client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.embedding_api_base,
        )
        # 异步客户端（新代码推荐）
        self.async_openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.embedding_api_base,
        )
        self.embedding_model = settings.embedding_model

    # ====== 向量操作 ======

    def get_dense_embeddings(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        获取稠密向量（Dense Vector）- 同步版本（兼容旧代码）
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

    async def aget_dense_embeddings(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        获取稠密向量（Dense Vector）- 异步原生版本

        真正的 async/await，不阻塞事件循环，把 10 秒延迟打回 100 毫秒
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = await self.async_openai_client.embeddings.create(
                model=self.embedding_model,
                input=batch,
            )
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

    def get_dense_embedding(self, text: str) -> List[float]:
        """获取单个文本的稠密向量 - 同步版本"""
        return self.get_dense_embeddings([text])[0]

    async def aget_dense_embedding(self, text: str) -> List[float]:
        """获取单个文本的稠密向量 - 异步原生版本"""
        embeddings = await self.aget_dense_embeddings([text])
        return embeddings[0]

    def get_sparse_embeddings(self, texts: List[str]) -> List[SparseVector]:
        """
        获取稀疏向量（Sparse Vector / BM25）

        Args:
            texts: 文本列表

        Returns:
            稀疏向量列表
        """
        if not FASTEMBED_AVAILABLE:
            return []

        model = get_sparse_model()
        sparse_vectors = []

        for text in texts:
            # fastembed 返回生成器，取第一个结果
            sparse_embedding = list(model.embed([text]))[0]
            sparse_vectors.append(SparseVector(
                indices=sparse_embedding.indices.tolist(),
                values=sparse_embedding.values.tolist(),
            ))

        return sparse_vectors

    def get_sparse_embedding(self, text: str) -> Optional[SparseVector]:
        """获取单个文本的稀疏向量"""
        vectors = self.get_sparse_embeddings([text])
        return vectors[0] if vectors else None

    # ====== 集合操作 ======

    def collection_exists(self, collection_name: Optional[str] = None) -> bool:
        """检查集合是否存在"""
        collection_name = collection_name or settings.qdrant_collection
        try:
            collections = self.qdrant_client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception:
            return False

    def create_collection(self, collection_name: Optional[str] = None, enable_hybrid: bool = True) -> None:
        """
        创建向量集合（支持混合检索）

        Args:
            collection_name: 集合名称
            enable_hybrid: 是否启用混合检索（Dense + Sparse）
        """
        collection_name = collection_name or settings.qdrant_collection

        if self.collection_exists(collection_name):
            return

        # 配置命名向量
        if enable_hybrid and FASTEMBED_AVAILABLE:
            # 混合模式：Dense + Sparse
            vectors_config = {
                self.DENSE_VECTOR_NAME: VectorParams(
                    size=self.DENSE_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            }
            sparse_vectors_config = {
                self.SPARSE_VECTOR_NAME: SparseVectorParams(
                    index=SparseIndexParams(),
                ),
            }
        else:
            # 纯向量模式
            vectors_config = VectorParams(
                size=self.DENSE_VECTOR_SIZE,
                distance=Distance.COSINE,
            )
            sparse_vectors_config = None

        self.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_vectors_config,
        )

    def create_payload_indexes(self, collection_name: Optional[str] = None) -> None:
        """为 metadata 字段创建索引，加速过滤查询"""
        collection_name = collection_name or settings.qdrant_collection

        for field in INDEXED_FIELDS:
            try:
                self.qdrant_client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            except Exception:
                # 索引可能已存在，忽略错误
                pass

    def ensure_collection(self, collection_name: Optional[str] = None, enable_hybrid: bool = True) -> None:
        """确保集合和索引存在（推荐在入库前调用）"""
        self.create_collection(collection_name, enable_hybrid)
        self.create_payload_indexes(collection_name)

    def delete_collection(self, collection_name: Optional[str] = None) -> None:
        """删除向量集合"""
        collection_name = collection_name or settings.qdrant_collection
        self.qdrant_client.delete_collection(collection_name=collection_name)

    # ====== 文档操作 ======

    def add_documents(
        self,
        documents: List[Document],
        collection_name: Optional[str] = None,
        enable_hybrid: bool = True,
        doc_id: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> List[str]:
        """
        添加已切分的文档到向量库

        Args:
            documents: 已切分的 Document 列表（由 MarkdownSemanticSplitter 生成）
            collection_name: 集合名称
            enable_hybrid: 是否生成稀疏向量（混合检索）
            doc_id: 关联的知识库文档 ID（写入每个 Point 的 payload，方便按文档删除）
            progress_callback: 进度回调函数 callback(current, total)

        Returns:
            插入的文档 ID 列表
        """
        if not documents:
            return []

        collection_name = collection_name or settings.qdrant_collection
        self.ensure_collection(collection_name, enable_hybrid)

        texts = [doc.page_content for doc in documents]
        total = len(documents)
        batch_size = 10

        all_ids = []

        # 分批处理：embedding + upsert
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_texts = texts[batch_start:batch_end]
            batch_docs = documents[batch_start:batch_end]

            # 生成稠密向量
            dense_vectors = self.get_dense_embeddings(batch_texts)

            # 生成稀疏向量（可选）
            sparse_vectors = []
            if enable_hybrid and FASTEMBED_AVAILABLE:
                sparse_vectors = self.get_sparse_embeddings(batch_texts)

            # 构建点
            ids = [str(uuid.uuid4()) for _ in batch_docs]
            points = []

            for i, (pid, doc) in enumerate(zip(ids, batch_docs)):
                # 判断集合是否支持混合检索
                if sparse_vectors and i < len(sparse_vectors):
                    vector = {
                        self.DENSE_VECTOR_NAME: dense_vectors[i],
                        self.SPARSE_VECTOR_NAME: sparse_vectors[i],
                    }
                else:
                    vector = dense_vectors[i]

                payload = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                }
                if doc_id:
                    payload["doc_id"] = doc_id

                points.append(PointStruct(
                    id=pid,
                    vector=vector,
                    payload=payload,
                ))

            # 批量插入
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=points,
            )

            all_ids.extend(ids)

            # 进度回调
            if progress_callback:
                progress_callback(batch_end, total)

        return all_ids

    def delete_by_doc_id(self, doc_id: str, collection_name: Optional[str] = None) -> None:
        """按 doc_id 删除该文档的所有向量点"""
        collection_name = collection_name or settings.qdrant_collection
        if not self.collection_exists(collection_name):
            return
        self.qdrant_client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                )
            ),
        )

    def count_by_doc_id(self, doc_id: str, collection_name: Optional[str] = None) -> int:
        """统计某个 doc_id 对应的向量点数"""
        collection_name = collection_name or settings.qdrant_collection
        if not self.collection_exists(collection_name):
            return 0
        result = self.qdrant_client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
            exact=True,
        )
        return result.count

    def search(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, str]] = None,
        use_hybrid: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        检索（支持纯向量和混合检索）

        Args:
            query: 查询文本
            collection_name: 集合名称
            top_k: 返回结果数量
            filter_conditions: 过滤条件，如 {"type": "normal", "H2": "益海嘉里简介"}
            use_hybrid: 是否使用混合检索（向量 + 关键词 BM25）

        Returns:
            检索结果列表
        """
        collection_name = collection_name or settings.qdrant_collection

        if not self.collection_exists(collection_name):
            return []

        # 构建过滤条件
        filter_obj = None
        if filter_conditions:
            filter_obj = Filter(
                must=[
                    FieldCondition(
                        key=f"metadata.{k}",
                        match=MatchValue(value=v),
                    )
                    for k, v in filter_conditions.items()
                ]
            )

        try:
            # 生成查询向量
            query_dense = self.get_dense_embedding(query)

            if use_hybrid and FASTEMBED_AVAILABLE:
                # 混合检索 - 使用 Qdrant 1.10+ 标准写法：双路并发 + RRF 融合
                query_sparse = self.get_sparse_embedding(query)

                results = self.qdrant_client.query_points(
                    collection_name=collection_name,
                    prefetch=[
                        # 第一路：稀疏向量（BM25/关键词）召回
                        models.Prefetch(
                            query=models.SparseVector(
                                indices=query_sparse.indices,
                                values=query_sparse.values,
                            ),
                            using=self.SPARSE_VECTOR_NAME,
                            limit=top_k,
                        ),
                        # 第二路：稠密向量（语义）召回
                        models.Prefetch(
                            query=query_dense,
                            using=self.DENSE_VECTOR_NAME,
                            limit=top_k,
                        ),
                    ],
                    # 开启 RRF (Reciprocal Rank Fusion) 融合
                    query=models.FusionQuery(fusion=models.Fusion.RRF),
                    limit=top_k,
                    query_filter=filter_obj,
                    with_payload=True,
                )
            else:
                # 纯向量检索 - 使用新版 query_points API
                results = self.qdrant_client.query_points(
                    collection_name=collection_name,
                    query=query_dense,
                    using=self.DENSE_VECTOR_NAME,
                    limit=top_k,
                    query_filter=filter_obj,
                    with_payload=True,
                )

            # 统一结果格式 - 直接获取 points 属性
            try:
                points = results.points
            except AttributeError:
                points = results if isinstance(results, list) else []

            formatted_results = []
            for point in points:
                # 兼容不同的返回格式
                if hasattr(point, 'payload'):
                    payload = point.payload or {}
                    formatted_results.append({
                        "content": payload.get("content"),
                        "metadata": payload.get("metadata"),
                        "score": getattr(point, 'score', 0),
                    })
                elif isinstance(point, tuple):
                    # 旧版 search 可能返回 tuple
                    formatted_results.append({
                        "content": point[0] if len(point) > 0 else None,
                        "metadata": point[1] if len(point) > 1 else {},
                        "score": point[2] if len(point) > 2 else 0,
                    })

            return formatted_results
        except Exception as e:
            print(f"Search failed: {e}")
            return []

    # ====== 异步接口封装 ======

    async def asearch(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, str]] = None,
        use_hybrid: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        异步检索 - 真正原生异步版本

        1. Embedding 使用 AsyncOpenAI（异步，不阻塞）
        2. Qdrant 查询使用 run_in_executor（避免阻塞事件循环）
        把 10 秒延迟打回 100 毫秒
        """
        import asyncio

        collection_name = collection_name or settings.qdrant_collection

        if not self.collection_exists(collection_name):
            return []

        try:
            # Step 1: 异步获取 Embedding（真正的 async/await，不阻塞）
            query_dense = await self.aget_dense_embedding(query)

            # Step 2: Qdrant 查询（在线程池中执行，避免阻塞事件循环）
            loop = asyncio.get_event_loop()

            def do_search():
                # 构建过滤条件
                filter_obj = None
                if filter_conditions:
                    filter_obj = Filter(
                        must=[
                            FieldCondition(
                                key=f"metadata.{k}",
                                match=MatchValue(value=v),
                            )
                            for k, v in filter_conditions.items()
                        ]
                    )

                if use_hybrid and FASTEMBED_AVAILABLE:
                    # 混合检索
                    query_sparse = self.get_sparse_embedding(query)

                    results = self.qdrant_client.query_points(
                        collection_name=collection_name,
                        prefetch=[
                            models.Prefetch(
                                query=models.SparseVector(
                                    indices=query_sparse.indices,
                                    values=query_sparse.values,
                                ),
                                using=self.SPARSE_VECTOR_NAME,
                                limit=top_k,
                            ),
                            models.Prefetch(
                                query=query_dense,
                                using=self.DENSE_VECTOR_NAME,
                                limit=top_k,
                            ),
                        ],
                        query=models.FusionQuery(fusion=models.Fusion.RRF),
                        limit=top_k,
                        query_filter=filter_obj,
                        with_payload=True,
                    )
                else:
                    # 纯向量检索
                    results = self.qdrant_client.query_points(
                        collection_name=collection_name,
                        query=query_dense,
                        using=self.DENSE_VECTOR_NAME,
                        limit=top_k,
                        query_filter=filter_obj,
                        with_payload=True,
                    )

                # 格式化结果
                try:
                    points = results.points
                except AttributeError:
                    points = results if isinstance(results, list) else []

                formatted_results = []
                for point in points:
                    if hasattr(point, 'payload'):
                        payload = point.payload or {}
                        formatted_results.append({
                            "content": payload.get("content"),
                            "metadata": payload.get("metadata"),
                            "score": getattr(point, 'score', 0),
                        })
                    elif isinstance(point, tuple):
                        formatted_results.append({
                            "content": point[0] if len(point) > 0 else None,
                            "metadata": point[1] if len(point) > 1 else {},
                            "score": point[2] if len(point) > 2 else 0,
                        })

                return formatted_results

            # 在线程池中执行 Qdrant 查询
            return await loop.run_in_executor(None, do_search)

        except Exception as e:
            print(f"Search failed: {e}")
            return []

    async def aadd_documents(
        self,
        documents: List[Document],
        collection_name: Optional[str] = None,
        enable_hybrid: bool = True,
    ) -> List[str]:
        """异步添加文档包装器"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.add_documents(documents, collection_name, enable_hybrid)
        )

    # 别名，保持向后兼容
    get_embeddings = get_dense_embeddings
    get_embedding = get_dense_embedding

    def add_texts(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
        collection_name: Optional[str] = None,
    ) -> List[str]:
        """
        [兼容接口] 添加原始文本到向量库
        """
        documents = []
        for i, text in enumerate(texts):
            doc_metadata = metadata[i] if metadata and i < len(metadata) else {}
            documents.append(Document(page_content=text, metadata=doc_metadata))

        return self.add_documents(documents, collection_name)


# 全局服务实例
qdrant_service = QdrantService()

# 向后兼容别名
rag_service = qdrant_service
