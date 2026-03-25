# API Contract & Database Schema

## 1. 数据库模式 (PostgreSQL)

**注意:** Python 库中**绝对不要**创建 `users` 表。用户的实体归 Java 管。

**Table: `chat_sessions`**
- `id` (PK, String, UUID)
- `user_id` (String, Nullable, Index) -> 存储 Java 端的真实用户 ID，并非外键。
- `guest_id` (String, Nullable, Index) -> 存储前端生成的访客 UUID。
- `title` (String)

**Table: `chat_messages`**
- `id` (PK, String, UUID)
- `session_id` (FK -> chat_sessions.id)
- `role` (Enum: 'user', 'assistant')
- `content` (Text)
- `citations` (JSONB) -> 存储参考的文档元数据。

## 2. 核心 API 端点 (供 Java 调用)

### 2.1 聊天与流式输出
- **POST `/internal/chat/stream`**
- **Payload:** `{ "guest_id": "...", "user_id": "...", "query": "..." }`
- **Response:** `text/event-stream` (SSE 协议持续输出 chunk)

### 2.2 历史会话查询
- **GET `/internal/chat/sessions`**
- **Query:** `?guest_id=xxx&user_id=yyy` (二者传其一)
- **Response:** 返回该实体名下的 `chat_sessions` 列表。

### 2.3 账号绑定过户 (访客转正)
- **POST `/internal/api/v1/chat/bind`**
- **Payload:** `{ "guest_id": "uuid-123", "user_id": "888" }`
- **Action:** 更新对应的 `chat_sessions` 的所有权。