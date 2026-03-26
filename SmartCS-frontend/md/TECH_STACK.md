# TECH_STACK（版本锁定清单）

目的：把前端实现所依赖的**包 / 依赖 / API 契约 / 工具链**锁定到**确切版本**，保证可复现构建与一致行为。

## 1. 运行环境（Runtime）

| 项目 | 锁定版本 | 说明 |
| --- | --- | --- |
| Node.js | 22.11.0 | 构建与本地开发运行时 |
| pnpm | 9.15.4 | 包管理器（建议强制使用） |
| packageManager 字段 | `pnpm@9.15.4` | 写入 `package.json`，阻止误用 npm/yarn |

## 2. 前端核心依赖（Dependencies）

| 包名 | 锁定版本 | 用途 |
| --- | ---: | --- |
| vue | 3.5.13 | Vue 3（Composition API + `<script setup>`） |
| vue-router | 4.5.0 | 路由（主站路由维持原逻辑；客服以按钮触发弹窗呈现，不新增客服 URL） |
| pinia | 2.2.6 | 状态管理（Visitor ID、会话、服务模式、连接实例等） |
| element-plus | 2.8.8 | 组件库（el-row/el-col、el-form、el-card、el-popover 等） |
| @element-plus/icons-vue | 2.3.2 | Element Plus 图标库（用于工具栏与状态图标） |
| axios | 1.7.9 | 常规 HTTP 请求 |
| @vueuse/core | 11.3.0 | 常用组合式工具（剪贴板、网络状态、事件监听等） |
| dayjs | 1.11.13 | 时间格式化（消息时间、导出等） |
| zod | 3.23.8 | 结构化卡片 JSON 的 schema 校验与容错降级 |
| mitt | 3.0.1 | 轻量事件总线（可选，用于组件解耦） |

## 3. 构建工具链（DevDependencies）

| 包名 | 锁定版本 | 用途 |
| --- | ---: | --- |
| vite | 5.4.10 | 本地开发与打包 |
| @vitejs/plugin-vue | 5.1.4 | Vue SFC 支持 |
| typescript | 5.6.3 | TS 编译器 |
| vue-tsc | 2.1.10 | Vue 类型检查 |
| eslint | 9.14.0 | Lint |
| @eslint/js | 9.14.0 | ESLint 基础规则集 |
| eslint-plugin-vue | 9.32.0 | Vue 规则 |
| prettier | 3.3.3 | 格式化 |
| postcss | 8.4.49 | CSS 处理 |
| autoprefixer | 10.4.20 | CSS 前缀 |
| sass | 1.80.5 | Sass（如使用） |

## 4. 测试与质量（可选但建议）

| 包名 | 锁定版本 | 用途 |
| --- | ---: | --- |
| vitest | 2.1.8 | 单元测试 |
| @vitest/ui | 2.1.8 | 测试 UI（可选） |
| jsdom | 25.0.1 | DOM 环境（组件测试） |
| @testing-library/vue | 8.1.0 | 组件测试（面向用户行为） |
| @testing-library/user-event | 14.5.2 | 交互模拟 |
| playwright | 1.49.1 | E2E 测试（关键路径：发消息、流式、转人工、导出） |

## 5. 按需引入与构建优化（Element Plus 推荐）

| 包名 | 锁定版本 | 用途 |
| --- | ---: | --- |
| unplugin-auto-import | 0.18.6 | 自动导入（ref/computed 等） |
| unplugin-vue-components | 0.27.5 | 组件按需引入（Element Plus） |

## 6. API 与协议（契约版本锁定）

说明：这里锁定的是**接口契约版本**与**消息/卡片 schema 版本**，用于前后端协作与回归测试基线。

### 6.0 交互集成形态（固定）
- 客服入口：主界面“智能客服”按钮
- 展示方式：点击后打开悬浮弹窗
- 路由策略：弹窗打开/关闭不改变当前 URL，不跳转独立客服页

### 6.1 通用 Header（固定键名）
- `X-Visitor-Id`: string（必传，免登录访客标识）
- `X-Page-Context`: string（可选，商品ID/分类等序列化后内容）
- `Authorization`: `Bearer <token>`（可选，仅登录后出现）

### 6.2 会话契约版本
- `api_version`: `2026-03-18.v1`
- `card_schema_version`: `2026-03-18.v1`

### 6.3 流式输出协议

| 通道 | 锁定协议版本 | 约束 |
| --- | --- | --- |
| SSE | `sse.v1` | `text/event-stream`；必须支持增量 token 与结束事件 |
| WebSocket | `ws.v1` | 必须支持：连接鉴权、心跳、增量 token、结束事件、错误事件 |

### 6.4 卡片类型枚举（card_schema_version = 2026-03-18.v1）

| type | 说明 | 关键字段（最小集） | 失败降级 |
| --- | --- | --- | --- |
| `contact_card` | 联系方式（可选） | `wechat,phone,qrcodeUrl` | 展示可复制文本（不依赖二维码） |
| `csat_card` | 评价卡片（可选） | `sessionId,scale=5` | 文本评价链接/入口 |

> 说明：当前版本为“仅对话能力”，暂不锁定 `course_card` / `teacher_card` / `lead_form`。

### 6.5 错误码（建议固定）

| code | 含义 | 前端统一处理 |
| --- | --- | --- |
| `NETWORK_ERROR` | 网络不可用 | 进入离线/重连 UI（FLOW: F18） |
| `RATE_LIMITED` | 频控 | 提示稍后重试，保留输入草稿 |
| `INVALID_SCHEMA` | 卡片不合法 | 降级为纯文本并记录错误 |
| `HUMAN_UNAVAILABLE` | 人工不可用 | 提示继续 AI 或留言 |

## 7. 浏览器能力基线（锁定到最低版本）

| 浏览器 | 最低版本 | 依赖能力 |
| --- | ---: | --- |
| Chrome | 120 | SSE、WebSocket、Clipboard API、File/Blob、Web Crypto（如用） |
| Edge | 120 | 同上 |
| Safari | 17.0 | SSE、WebSocket、Clipboard API（兼容性需验证） |

## 8. 锁定策略（落地规则）

### 8.1 依赖锁定
- 必须存在且提交：`pnpm-lock.yaml`
- 依赖版本必须精确（不使用 `^` / `~`）

### 8.2 构建可复现
- Node/pnpm 版本固定：CI 与本地一致
- 生产构建与本地构建输出一致（同一 lockfile + 同一 Node/pnpm）

### 8.3 版本升级流程
- 任何依赖升级都必须：更新本文件对应版本 + 更新 lockfile + 跑通 lint/typecheck/test（如配置）
