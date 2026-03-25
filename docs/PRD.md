# Product Requirements Document (PRD): AI 内部微服务引擎

## 1. 系统定位
本项目是一个纯后端、无 UI 的内部微服务（AI Engine）。它不直接面向公网用户，而是作为公司主业务系统（Java 网关）的底层算力支撑。

## 2. 核心职责 (In Scope)
1. **统一会话管理:** 存储并管理访客 (`guest_id`) 和正式用户 (`user_id`) 的大模型聊天记录。
2. **多模态 RAG 问答:** 接收 Java 端透传的问题，检索内部 Qdrant 向量库，组装 Prompt，调用 LLM，并将结果以 SSE (Server-Sent Events) 流式返回。
3. **数据认领转移:** 提供接口，当 Java 端完成访客注册时，将原 `guest_id` 名下的聊天记录过户给正式 `user_id`。
4. **知识库解析:** 接收 Java 端发来的文档 URL，异步执行文档下载、版面分析、切块 (Chunking) 与向量化入库。

## 3. 明确不在范围内 (Out of Scope)
- 任何前端页面的渲染与交互。
- 用户的注册、登录、密码找回、Token 发放。
- C 端的高频限流防刷（由 Java 网关层负责拦截）。

## 4. 成功标准
- 提供极高稳定性的 SSE 流式接口，首字响应延迟 < 2 秒。
- 接口契约严谨，Java 端对接无障碍。