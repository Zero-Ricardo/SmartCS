# App Flow & Routing

## 1. C端流程：访客问答与注册转化
**触发点:** 用户打开前台聊天界面 `/chat`。
**序列:**
1. **初始化:** 页面加载，前端检查 LocalStorage 是否有 `guest_id` 和 `access_token`。
   - 如果都没，生成一个新的 UUID 存入 `guest_id`。
   - 调用 `/api/chat/history` (Header 带上 `guest_id` 或 `Token`) 拉取会话列表。
2. **日常对话:** 用户发送消息，触发 SSE 流式响应，本地追加气泡。
3. **关键节点 - 注册转化:**
   - 用户点击“注册/登录”按钮。
   - 填写信息提交后，前端在请求体中附带当前的 `guest_id` 发送给 `/api/auth/register` 或 `/api/auth/login`。
   - 后端完成验证后，将该 `guest_id` 对应的所有 `conversations` 的 `user_id` 字段更新为当前真实用户 ID。
   - 前端拿到 Token，清除或保留 `guest_id` 均可，后续请求统一改用 Token，页面无需刷新，历史记录已在云端绑定。

## 2. B端流程：管理后台
**路由:** `/admin/*`
**序列:**
1. 管理员访问 `/admin/login` 获取 Token。
2. **知识库管理:** 访问 `/admin/knowledge` -> 上传文档 -> 触发异步解析。
3. **对话审计:** 访问 `/admin/audits` -> 查看所有访客和注册用户的对话流。