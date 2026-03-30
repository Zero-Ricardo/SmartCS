# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

SmartCS 是一个纯后端 AI 微服务引擎，不直接面向公网用户，而是作为公司主业务系统（Java 网关）的底层算力支撑。

**核心职责:**
- 统一会话管理（访客 `guest_id` 和正式用户 `user_id`）
- 多模态 RAG 问答（SSE 流式返回）
- 数据认领转移（访客注册时聊天记录过户）
- 知识库解析（文档向量化入库）
- 消息反馈（有用/无用评价）

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
- OpenAI SDK (调用阿里云 DashScope API)
- Vue 3 + TypeScript + Vite + Element Plus (前端，仅演示用)

## 启动命令

```bash
# 启动依赖容器（PostgreSQL + Qdrant）
docker-compose up -d postgres qdrant

# 安装依赖
uv sync

# 运行数据库迁移
uv run alembic upgrade head

# 生成新迁移
uv run alembic revision --autogenerate -m "description"

# 启动后端服务
uv run uvicorn app.main:app --reload

# 全栈启动（包含前端 Nginx）
docker-compose up -d --build
```

## 测试命令

```bash
# 所有测试脚本位于 test/ 目录，直接用 uv run 执行
uv run python test/test_llm_embedding.py    # LLM + Embedding 连通性
uv run python test/test_sse.py              # SSE 流式输出
uv run python test/test_rag.py              # 完整 RAG 流程
uv run python test/test_feedback.py         # 反馈接口
uv run python test/test_knowledge_ingest.py # 知识库导入
uv run python test/test_text_splitter.py    # 文本切分
uv run python test/test_api.py              # API 集成测试

# RAG 评估脚本
uv run python scripts/eval_retrieval.py

# 删除 Qdrant 集合
uv run python scripts/delete_collection.py
```

## 项目结构

```
app/
├── main.py                 # FastAPI 入口（生命周期管理、路由注册、代理禁用）
├── core/                   # 基础设施层
│   ├── config.py           # Pydantic Settings（.env 加载，所有配置集中管理）
│   ├── database.py         # SQLAlchemy async 连接池 + get_db 依赖注入
│   └── security.py         # X-Internal-Secret 鉴权装饰器
├── models/chat.py          # ChatSession / ChatMessage / ChatFeedback ORM
├── schemas/chat.py         # Pydantic 请求/响应模型
├── api/                    # API 路由层（纯接客，不含业务逻辑）
│   ├── chat.py             # 聊天、会话、反馈接口
│   └── knowledge.py        # 知识库导入接口
├── agent/                  # LangGraph 智能体
│   ├── state.py            # AgentState 状态定义
│   ├── nodes.py            # 节点函数（analyze/retrieve/generate）
│   └── graph.py            # 图编排（stream_agent 是主入口）
└── services/               # 外部资源封装
    ├── qdrant_service.py    # 向量检索（Dense + Sparse 混合检索 + RRF 融合）
    ├── llm_service.py      # LLM 流式输出（OpenAI SDK）
    ├── db_service.py       # 数据库操作封装
    └── text_splitter.py    # Markdown 语义切分器
```

## 核心架构：RAG 请求流程

```
用户问题 → POST /internal/chat/stream
    │
    ├─ 1. chat.py: 创建/复用会话，保存用户消息，查历史消息
    │
    ├─ 2. graph.py → stream_agent():
    │     ├─ analyze_node(): 规则路由（<1ms），判断 need_rag / direct_answer
    │     ├─ [retrieve_node()]: Dense+Sparse 混合检索 → RRF 融合（top_k=3）
    │     └─ llm_service.stream_chat(): 流式生成回答
    │
    ├─ 3. SSE 事件流：session → chunk* → citations → done
    │
    └─ 4. chat.py: 保存 AI 回复到数据库
```

**关键设计：**
- 消息 ID 由前端预生成（`user_message_id`、`ai_message_id`），后端直接使用
- `analyze_node` 已从 LLM 改为纯规则路由，延迟 <1ms
- 历史消息取最近 6 条（3 轮）作为上下文
- `main.py` 首行禁用代理，防止 Qdrant 连接走代理导致 502

## 数据库模型

- `chat_sessions`: id, user_id (nullable), guest_id (nullable), title, created_at, updated_at
- `chat_messages`: id, session_id (FK), role (user/assistant), content, citations (JSONB), created_at
- `chat_feedbacks`: id, message_id (FK), session_id (FK), feedback_type (up/down), reason, created_at

索引：`chat_sessions(user_id, guest_id)` 复合索引，`chat_feedbacks(feedback_type, created_at)`。

迁移文件在 `alembic/versions/`，当前共 3 个迁移。

## API 端点规范

| 端点 | 方法 | 用途 |
|------|------|------|
| `/health` | GET | 健康检查（无需鉴权） |
| `/internal/chat/stream` | POST | SSE 流式聊天（RAG + LLM） |
| `/internal/chat/sessions` | GET | 查询会话列表 |
| `/internal/chat/messages` | GET | 查询历史消息 |
| `/internal/chat/bind` | POST | 访客数据过户 |
| `/internal/chat/feedback` | POST | 消息反馈（有用/无用） |
| `/internal/knowledge/ingest` | POST | 异步知识库导入（后台任务） |
| `/internal/knowledge/ingest/sync` | POST | 同步知识库导入（测试用） |

所有 `/internal/*` 端点必须在 Header 中携带 `X-Internal-Secret: <密钥>`。

## SSE 流事件协议

聊天接口返回多类型 SSE 事件：
1. `event: session` — 携带 session_id（新建会话时）
2. `data: <text>` — 文本块（逐块流式输出）
3. `event: citations` — 引用来源列表
4. `data: [DONE]` — 流结束标记

## 语义切分策略（text_splitter.py）

知识库文档使用 `MarkdownSemanticSplitter` 进行语义化切分：

1. **按 Markdown 标题层级粗切** — 每个 H1-H6 标题下的内容作为一个语义单元
2. **标题前缀注入** — 每个 chunk 开头拼接标题路径，如 `【文档标题 > H2 > H3】`
3. **图片描述块独立处理** — `> 🖼` 块不打散，标记 `type="image_description"`
4. **超长正文二次细切** — 按段落/句子切分，但**所有子块继承父级 Metadata**

## 混合检索策略（qdrant_service.py）

采用 Dense + Sparse 混合检索：

| 向量类型 | 模型 | 用途 |
|---------|------|------|
| Dense (稠密) | text-embedding-v4 | 语义理解 |
| Sparse (稀疏) | fastembed BM25 | 关键词匹配 |

**Qdrant 1.10+ 原生 API**：`query_points` + `Prefetch` + `FusionQuery.RRF`

## 配置管理

所有配置通过 `app/core/config.py` 的 `Settings` 类管理，从 `.env` 文件加载：

| 配置项 | 说明 |
|-------|------|
| `DATABASE_URL` | PostgreSQL 连接串（psycopg 异步驱动） |
| `INTERNAL_SECRET` | 服务间鉴权密钥 |
| `OPENAI_API_KEY` | LLM API Key |
| `OPENAI_API_BASE` | LLM API 地址（阿里云 DashScope） |
| `fast_model` | 轻量模型（已弃用，改用规则路由） |
| `quality_model` | 生成模型（默认 ） |
| `embedding_api_base` | Embedding API 地址 |
| `embedding_model` | 嵌入模型（默认 text-embedding-v4） |
| `QDRANT_HOST` / `QDRANT_PORT` | Qdrant 连接 |
| `qdrant_collection` | 向量集合名称（默认 pxb） |

Docker Compose 中后端容器会覆盖 `DATABASE_URL` 和 `QDRANT_HOST` 指向容器内服务。

## 核心设计约束

1. **不创建 users 表** — 用户实体由 Java 网关管理
2. **S2S 鉴权** — 仅使用 `X-Internal-Secret` header，Java 网关负责 JWT 校验
3. **异步优先** — 所有 I/O 操作使用 async/await
4. **代理禁用** — `main.py` 首行清空代理环境变量
5. **API 层不含业务逻辑** — `api/` 只做请求解析和响应组装，AI 逻辑在 `agent/` 和 `services/`

## 常见错误处理

- **pydantic v2**: `class Config` → `model_config = {"extra": "ignore"}`
- **Qdrant 502 Bad Gateway**: 清空代理环境变量 `os.environ["HTTP_PROXY"] = ""`
- **HuggingFace 下载超时**: 设置镜像 `os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"`
- **langchain 导入**: `from langchain.text_splitter` → `from langchain_text_splitters`
- **阿里云 DashScope**: 使用国际域名 `dashscope-intl.aliyuncs.com`
- **.env 格式**: 等号两边不能有空格

## 评估脚本配置参数

```python
# scripts/eval_retrieval.py
COLLECTION_NAME = "pxb"          # Qdrant 集合名称
TOP_K = 5                       # 检索返回数量
CHUNK_SIZE = 500                # 切分块大小
CHUNK_OVERLAP = 100             # 切分重叠大小
INJECT_TITLE_PREFIX = True       # 标题前缀注入
USE_HYBRID = True               # 混合检索开关
```

## RAG 评估结果（2026-03-23）

| 指标 | Clear Question | Vague Question | 综合 |
|------|---------------|---------------|------|
| **Hit@5** | 94.8% (91/96) | 88.5% (85/96) | **91.7%** |
| **MRR** | 0.9127 | 0.8307 | **0.8717** |

测试集：48 个文档，96 条用例

## 项目进度

Phase 5 阶段（目录重构 + LangGraph）完成，Phase 5.4 集成测试完成。
- RAG 评估：Hit@5 91.7%，MRR 0.8717
- 反馈系统（chat_feedbacks 表）已上线
- 待完成：LangGraph 状态流转验证、Rerank 重排序（可选）
