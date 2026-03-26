# System Architecture & Data Flow

## 1. 网络边界与鉴权规则
- **内部隔离:** 本 FastAPI 服务运行在内网，不暴露公网 IP。
- **服务间鉴权 (S2S):** 所有请求必须在 Header 中携带 `X-Internal-Secret: <静态内部密钥>`。本服务只认此 Key，不校验任何 JWT 或用户身份。

## 2. 核心业务数据流转

### 场景 A: 纯访客对话
1. Java 收到前端请求，提取出 `guest_id = "uuid-123"`。
2. Java 调用 Python `/api/chat/stream`，请求体包含 `guest_id`。
3. Python 在本地 `chat_sessions` 表中查找或新建属于该 `guest_id` 的会话，流式输出 AI 答案。

### 场景 B: 访客注册转化 (关键节点)
1. Java 端完成用户的注册，生成了数据库真实的 `user_id = 888`。
2. Java 发现该用户注册前是访客，立刻调用 Python 的 `/api/chat/bind`。
3. Python 执行 SQL：`UPDATE chat_sessions SET user_id = '888' WHERE guest_id = 'uuid-123'`。完成历史数据过户。

### 场景 C: 异步知识库处理
1. Java 端将文件存入 OSS。
2. Java 调用 Python `/api/knowledge/ingest`，传入 `file_url`。
3. Python 立即返回 HTTP 200 (Task Created)。后台启动 Celery 或 BackgroundTasks 进行向量化。