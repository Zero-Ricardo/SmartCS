# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

SmartCS 是一个纯后端 AI 微服务引擎，不直接面向公网用户，而是作为公司主业务系统（Java 网关）的底层算力支撑。

**核心职责:**
- 统一会话管理（访客 `guest_id` 和正式用户 `user_id`）
- 多模态 RAG 问答（SSE 流式返回）
- 数据认领转移（访客注册时聊天记录过户）
- 知识库解析（文档向量化入库）

**不在范围内:**
- 任何前端页面
- 用户注册/登录/JWT（由 Java 网关负责）
- 限流防刷（由 Java 网关负责）

## 技术栈

- Python 3.12 + uv 包管理
- FastAPI 0.110.0 + Uvicorn 0.28.0
- PostgreSQL 16 + SQLAlchemy 2.0.28 + psycopg (异步驱动)
- Qdrant v1.10+ (向量数据库)
- qdrant-client 1.17.1
- fastembed (BM25 稀疏向量)
- LangChain 0.3.x
- OpenAI SDK (调用阿里云 DashScope 国际版 API)

## 项目结构

```
app/
├── main.py                 # FastAPI 入口
├── core/                   # 基础设施层
│   ├── config.py           # Pydantic Settings 配置
│   ├── database.py         # SQLAlchemy async 连接池
│   └── security.py         # X-Internal-Secret 鉴权装饰器
├── models/chat.py          # ChatSession / ChatMessage ORM
├── schemas/chat.py         # Pydantic 请求/响应模型
├── api/                    # API 路由层
│   ├── dependencies.py     # FastAPI 依赖注入
│   ├── chat.py             # 聊天相关接口
│   └── knowledge.py        # 知识库导入接口
├── agent/                  # LangGraph 智能体（架构预留）
│   ├── state.py            # AgentState 状态定义
│   ├── nodes.py            # 节点函数（intent/rewrite/retrieve/generate）
│   └── graph.py            # 有向图编译
└── services/               # 外部资源封装
    ├── qdrant_service.py    # 向量检索服务（含混合检索）
    ├── llm_service.py      # LLM 流式输出
    ├── db_service.py       # 数据库操作封装
    └── text_splitter.py    # Markdown 语义切分器

scripts/
├── eval_retrieval.py       # RAG 评估脚本
└── delete_collection.py    # 删除 Qdrant 集合
```

## 核心设计约束

1. **不创建 users 表** — 用户实体由 Java 网关管理
2. **S2S 鉴权** — 仅使用 `X-Internal-Secret` header，Java 网关负责 JWT 校验
3. **异步优先** — 所有 I/O 操作使用 async/await
4. **代理禁用** — qdrant_service.py 初始化时清空代理环境变量

## API 端点规范

| 端点 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/internal/chat/stream` | POST | SSE 流式聊天（RAG + LLM） |
| `/internal/chat/sessions` | GET | 查询会话列表 |
| `/internal/chat/bind` | POST | 访客数据过户 |
| `/internal/knowledge/ingest` | POST | 异步知识库导入（后台任务） |
| `/internal/knowledge/ingest/sync` | POST | 同步知识库导入（测试用） |

所有 `/internal/*` 端点必须在 Header 中携带 `X-Internal-Secret: <密钥>`。

## 数据库模型

- `chat_sessions`: id, user_id (nullable), guest_id (nullable), title, created_at, updated_at
- `chat_messages`: id, session_id (FK), role (user/assistant), content, citations (JSONB), created_at

索引：`chat_sessions` 上的 `(user_id, guest_id)` 复合索引。

## 语义切分策略（text_splitter.py）

知识库文档使用 `MarkdownSemanticSplitter` 进行语义化切分：

1. **按 Markdown 标题层级粗切** — 每个 H1-H6 标题下的内容作为一个语义单元
2. **标题前缀注入** — 每个 chunk 开头拼接标题路径，如 `【文档标题 > H2 > H3】`
3. **图片描述块独立处理** — `> 🖼` 块不打散，标记 `type="image_description"`
4. **超长正文二次细切** — 按段落/句子切分，但**所有子块继承父级 Metadata**

## 混合检索策略（qdrant_service.py）

采用工业级 Dense + Sparse 混合检索：

| 向量类型 | 模型 | 用途 |
|---------|------|------|
| Dense (稠密) | text-embedding-v3 | 语义理解 |
| Sparse (稀疏) | fastembed BM25 | 关键词匹配 |

**Qdrant 1.10+ 原生 API**：`query_points` + `Prefetch` + `FusionQuery.RRF`

## RAG 评估结果（2026-03-23）

| 指标 | Clear Question | Vague Question | 综合 |
|------|---------------|---------------|------|
| **Hit@5** | 94.8% (91/96) | 88.5% (85/96) | **91.7%** |
| **MRR** | 0.9127 | 0.8307 | **0.8717** |

测试集：48 个文档，96 条用例（question_clear + question_vague）

## 启动命令

```bash
# 启动依赖容器
docker-compose up -d

# 运行数据库迁移（如需要）
uv run alembic upgrade head

# 启动服务
uv run uvicorn app.main:app --reload
```

## 测试命令

```bash
# RAG 评估（修改 scripts/eval_retrieval.py 配置后运行）
uv run python scripts/eval_retrieval.py

# 删除 Qdrant 集合
uv run python scripts/delete_collection.py

# LLM + Embedding 连通性
uv run python test/test_llm_embedding.py

# SSE 流式输出
uv run python test/test_sse.py

# 完整 RAG 流程
uv run python test/test_rag.py
```

## 评估脚本配置参数

```python
# scripts/eval_retrieval.py

COLLECTION_NAME = "pxb"          # Qdrant 集合名称
TOP_K = 5                       # 检索返回数量
CHUNK_SIZE = 500                # 切分块大小
CHUNK_OVERLAP = 100             # 切分重叠大小
INJECT_TITLE_PREFIX = True       # 标题前缀注入
USE_HYBRID = True             # 混合检索开关
```

## 常见错误处理

- **pydantic v2**: `class Config` → `model_config = {"extra": "ignore"}`
- **Qdrant 502 Bad Gateway**: 清空代理环境变量 `os.environ["HTTP_PROXY"] = ""`
- **HuggingFace 下载超时**: 设置镜像 `os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"`
- **langchain 导入**: `from langchain.text_splitter` → `from langchain_text_splitters`
- **阿里云 DashScope**: 使用国际域名 `dashscope-intl.aliyuncs.com`
- **.env 格式**: 等号两边不能有空格

## 项目进度

Phase 5 阶段（目录重构 + LangGraph）完成，Phase 5.4 集成测试完成。
- RAG 评估：Hit@5 91.7%，MRR 0.8717
- 待完成：LangGraph 状态流转验证、Rerank 重排序（可选）
