# Step-by-Step Implementation Plan

**执行规则:** AI 助手必须严格按照以下顺序编写代码，严禁自行添加未经授权的中间件或前端代码。

## Phase 1: 基础设施构建 ✅

- [x] 1.1 初始化 FastAPI 应用目录结构 (routers, models, services, core)
- [x] 1.2 编写 `core/security.py`，实现 X-Internal-Secret 校验依赖
- [x] 1.3 使用 SQLAlchemy 定义 `chat_sessions` 和 `chat_messages` 模型，配置 Alembic 迁移

## Phase 2: 接口骨架与数据绑定 ✅

- [x] 2.1 实现 `/internal/chat/sessions` 接口
- [x] 2.2 实现 `/internal/chat/bind` 接口，处理 guest_id → user_id 过户

## Phase 3: 流式引擎 (Mock 阶段) ✅

- [x] 3.1 编写 `/internal/chat/stream` 路由
- [x] 3.2 使用异步生成器测试 StreamingResponse

## Phase 4: RAG 与 LangChain 缝合 ✅

- [x] 4.1 引入 Qdrant 客户端，编写 `services/rag_service.py`
- [x] 4.2 接入真实 LLM，实现"检索 → 组装 Prompt → 流式输出 → 保存数据库"闭环

## Phase 5: 目录重构 + LangGraph 智能体 ✅

### 5.1 目录重构 ✅
- [x] 5.1.1 重命名 `routers/` → `api/`
- [x] 5.1.2 新增 `schemas/chat.py` - Pydantic 数据校验层
- [x] 5.1.3 新增 `api/dependencies.py` - FastAPI 依赖注入
- [x] 5.1.4 新增 `services/db_service.py` - 数据库操作封装
- [x] 5.1.5 重命名 `services/rag_service.py` → `services/qdrant_service.py`
- [x] 5.1.6 更新 `main.py` 和相关导入

### 5.2 LangGraph 智能体 ✅
- [x] 5.2.1 新增 `agent/state.py` - 定义状态机 (AgentState)
- [x] 5.2.2 新增 `agent/nodes.py` - 实现节点函数
  - `intent_node`: 意图识别
  - `rewrite_node`: 问题改写
  - `retrieve_node`: 向量检索
  - `generate_node`: LLM 生成
- [x] 5.2.3 新增 `agent/graph.py` - 编译有向图
- [x] 5.2.4 新增 `agent/__init__.py` - 导出 compiled_graph

### 5.3 知识库导入接口 ✅
- [x] 5.3.1 实现 `/internal/knowledge/ingest` 接口
- [x] 5.3.2 支持批量导入企业 MD 文档
- [x] 5.3.3 编写知识库导入测试脚本

### 5.4 集成测试 ✅
- [x] 5.4.1 使用真实企业数据测试 RAG 效果
- [x] 5.4.2 语义切分策略（标题前缀注入）
- [x] 5.4.3 混合检索（Dense + Sparse/BM25）
- [x] 5.4.4 Qdrant 1.10+ 原生混合检索
- [ ] 5.4.5 验证 LangGraph 状态流转

---

## Phase 6: 生产化准备 🚧

- [ ] 6.1 错误处理与日志优化
- [ ] 6.2 Docker 镜像构建
- [ ] 6.3 API 文档完善
- [ ] 6.4 压力测试

---

## 目标目录结构

```
SmartCS/
├── app/
│   ├── main.py                 # FastAPI 启动点
│   ├── core/                   # 基础设施层
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/                 # 数据持久层 (SQLAlchemy)
│   │   └── chat.py
│   ├── schemas/                # 数据校验层 (Pydantic)
│   │   └── chat.py
│   ├── api/                    # API 接口层
│   │   ├── dependencies.py
│   │   ├── chat.py
│   │   └── knowledge.py
│   ├── agent/                  # LangGraph 智能体中枢
│   │   ├── state.py
│   │   ├── nodes.py
│   │   └── graph.py
│   └── services/               # 外部资源服务层
│       ├── qdrant_service.py    # 向量检索（含混合检索）
│       ├── llm_service.py       # LLM 流式输出
│       ├── db_service.py        # 数据库操作
│       └── text_splitter.py     # 语义切分器
├── scripts/
│   ├── eval_retrieval.py       # RAG 评估脚本
│   └── delete_collection.py     # 删除 Qdrant 集合
├── test/
│   ├── test_llm_embedding.py
│   ├── test_sse.py
│   ├── test_rag.py
│   └── test_knowledge_ingest.py
├── alembic/
├── docs/
├── docker-compose.yml
├── pyproject.toml
└── .env
```

---

## 评估结果（2026-03-23）

| 指标 | Clear Question | Vague Question | 综合 |
|------|---------------|---------------|------|
| **Hit@5** | 94.8% (91/96) | 88.5% (85/96) | **91.7%** |
| **MRR** | 0.9127 | 0.8307 | **0.8717** |

测试集：48 个文档，96 条用例（question_clear + question_vague）
