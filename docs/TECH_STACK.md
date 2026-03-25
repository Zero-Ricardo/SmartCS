# Tech Stack Specifications

**系统要求:** 严格锁定版本。这是一个纯后端 API 服务。

## 核心框架
- **Web 框架:** FastAPI (0.110.0)
- **ASGI 服务器:** Uvicorn (0.28.0)
- **Python 版本:** 3.12+

## 数据库与持久化
- **关系型数据库:** PostgreSQL 16
- **ORM:** SQLAlchemy (2.0.28) + psycopg (纯异步操作)
- **向量数据库:** Qdrant v1.10+ (latest)
- **Python SDK:** qdrant-client (1.17.1)

## AI 与大模型引擎
- **编排框架:** LangChain (0.3.x)
- **模型通信:** OpenAI 官方 SDK (用于兼容所有类 OpenAI API 格式的大模型)
- **Embedding:** 阿里云 DashScope 国际版 (text-embedding-v3)
- **LLM:** 阿里云 DashScope 国际版 (qwen3.5-plus)

## RAG 检索
- **稠密向量:** text-embedding-v3 (1024 维，语义理解)
- **稀疏向量:** fastembed BM25 (关键词匹配)
- **混合检索:** Qdrant 原生 Prefetch + RRF 融合

## 包管理
- **Python 包管理器:** uv

## 测试
- **框架:** pytest
