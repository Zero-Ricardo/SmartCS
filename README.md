<<<<<<< HEAD
# SmartCS AI Engine

一个基于 RAG（检索增强生成）的智能客服微服务引擎，提供流式问答、会话管理和知识库检索功能。

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI 0.110+ / Uvicorn |
| 数据库 | PostgreSQL 16 + SQLAlchemy 2.0 |
| 向量数据库 | Qdrant |
| LLM | 阿里云 DashScope () |
| 嵌入模型 | text-embedding-v3 |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus |
| 容器化 | Docker + docker-compose |

## 项目结构

```
SmartCS/
├── app/                        # 后端代码
│   ├── main.py                 # FastAPI 入口
│   ├── core/                   # 基础设施
│   │   ├── config.py           # 配置管理
│   │   ├── database.py         # 数据库连接
│   │   └── security.py         # 鉴权装饰器
│   ├── api/                    # API 路由
│   │   ├── chat.py             # 聊天接口
│   │   └── knowledge.py        # 知识库接口
│   ├── agent/                  # LangGraph 智能体
│   │   ├── state.py            # 状态定义
│   │   ├── nodes.py            # 节点函数
│   │   └── graph.py            # 图编排
│   ├── services/               # 外部服务封装
│   │   ├── llm_service.py      # LLM 调用
│   │   ├── qdrant_service.py   # 向量检索
│   │   └── db_service.py       # 数据库操作
│   ├── models/                 # ORM 模型
│   └── schemas/                # Pydantic 模型
├── SmartCS-frontend/           # 前端代码
│   ├── src/
│   │   ├── shared/api/         # API 调用
│   │   ├── entities/chat/      # 聊天模块
│   │   └── widgets/chat/       # UI 组件
│   ├── Dockerfile
│   └── nginx.conf
├── alembic/                    # 数据库迁移
├── scripts/                    # 工具脚本
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## 快速开始

### 环境要求

- Docker & Docker Compose
- Python 3.12+ (本地开发)
- Node.js 20+ / pnpm (本地前端开发)

### 1. 克隆项目

```bash
git clone https://github.com/your-username/smartcs.git
cd smartcs
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
vim .env
```

关键配置项：

```bash
# 数据库
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/smartcs

# LLM (阿里云 DashScope)
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=[image_uploaded] Embedding
EMBEDDING_API_BASE=[image_uploaded] 向量数据库
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=smartcs_knowledge

# 内部鉴权
INTERNAL_SECRET=your-internal-secret
```

### 3. 启动服务

**方式一：Docker Compose（推荐）**

```bash
# 启动所有服务
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 运行数据库迁移
docker-compose exec smartcs-backend uv run alembic upgrade head
```

访问：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

**方式二：本地开发**

```bash
# 终端 1：启动依赖服务
docker-compose up -d postgres qdrant

# 终端 2：启动后端
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 终端 3：启动前端
cd SmartCS-frontend
pnpm install
pnpm dev
```

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/internal/chat/stream` | POST | SSE 流式聊天 |
| `/internal/chat/sessions` | GET | 查询会话列表 |
| `/internal/chat/messages` | GET | 查询历史消息 |
| `/internal/chat/bind` | POST | 访客数据过户 |
| `/internal/knowledge/ingest` | POST | 知识库导入 |

所有 `/internal/*` 接口需要 Header：
```
X-Internal-Secret: <your-internal-secret>
```

### 流式聊天示例

```bash
curl -X POST "http://localhost:8000/internal/chat/stream" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: your-internal-secret" \
  -d '{"query": "培训宝是什么？", "guest_id": "visitor-001"}' \
  --no-buffer
```

## 知识库管理

### 导入文档

```bash
curl -X POST "http://localhost:8000/internal/knowledge/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: your-internal-secret" \
  -d '{
    "documents": [
      {
        "content": "# 文档标题\n\n文档内容...",
        "source": "https://example.com/doc",
        "doc_title": "示例文档"
      }
    ]
  }'
```

### 评估检索效果

```bash
uv run python scripts/eval_retrieval.py
```

## RAG 架构

```
用户问题
    │
    ▼
┌─────────────────┐
│  意图分析节点    │  ← 本地规则路由 (<1ms)
│  analyze_node   │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
need_rag   direct_answer
    │
    ▼
┌─────────────────┐
│  向量检索节点    │  ← Dense + Sparse 混合检索
│ retrieve_node   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM 生成节点    │  ← 流式输出 (SSE)
│ generate_node   │
└─────────────────┘
         │
         ▼
      回答 + 引用
```

## 数据库模型

### chat_sessions（会话表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | VARCHAR(64) | 用户 ID |
| guest_id | VARCHAR(64) | 访客 ID |
| title | VARCHAR(255) | 会话标题 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### chat_messages（消息表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| session_id | UUID | 会话 ID (FK) |
| role | ENUM | user / assistant |
| content | TEXT | 消息内容 |
| citations | JSONB | 引用来源 |
| created_at | DATETIME | 创建时间 |

## 配置说明

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| DATABASE_URL | 是 | PostgreSQL 连接字符串 |
| OPENAI_API_KEY | 是 | LLM API Key |
| OPENAI_API_BASE | 是 | API Base URL |
| QDRANT_HOST | 是 | Qdrant 主机 |
| QDRANT_PORT | 是 | Qdrant 端口 |
| INTERNAL_SECRET | 是 | 内部接口鉴权密钥 |
| DEBUG | 否 | 调试模式 |

### 模型配置

```python
# config.py
fast_model: str = ""      # 意图分析（已弃用，改用规则）
quality_model: str = ""   # 文本生成
embedding_model: str = "text-embedding-v3"
```

## 开发指南

### 运行测试

```bash
# LLM 连通性测试
uv run python test/test_llm_embedding.py

# RAG 流程测试
uv run python test/test_rag.py

# SSE 流式测试
uv run python test/test_sse.py
```

### 数据库迁移

```bash
# 生成迁移
uv run alembic revision --autogenerate -m "description"

# 执行迁移
uv run alembic upgrade head

# 回滚
uv run alembic downgrade -1
```

### 清空向量库

```bash
uv run python scripts/delete_collection.py
```

## 部署

### Docker 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f smartcs-backend
```

### 生产环境注意事项

1. 修改 `INTERNAL_SECRET` 为强密码
2. 配置 HTTPS（通过 Nginx 或云服务）
3. 设置数据库定期备份
4. 配置日志收集和监控

## 性能指标

| 指标 | 值 |
|------|-----|
| RAG Hit@5 | 91.7% |
| RAG MRR | 0.8717 |
| 意图分析延迟 | <1ms |
| 首字节时间 | ~3s |

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request
=======
# SmartCS
This is my first ai project

##
waiting my next upgrade

##
a upgrade in branch ricardo
a upgrade in branch ricardo
a upgrade in branch ricardo
>>>>>>> ccf230fdb4c35d76fc8c4248ef386bb338f94a2c
