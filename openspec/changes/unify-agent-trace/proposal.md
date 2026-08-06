## Why

当前聊天 Agent、AIOps 诊断、工具审计、后台任务和 HTTP 请求分别使用 `requestId`、工具调用 ID、诊断任务 ID 等局部标识，无法从一次用户操作稳定追踪到 Agent 阶段、工具调用、结果与错误。岗位要求强调 Agent 执行 Trace、自动评测与执行效率分析，因此需要先建立统一、可查询且具备权限隔离的 Trace 底座。

## What Changes

- 建立 owner 范围的统一 Agent Trace 与 Span 数据模型，覆盖聊天和 AIOps 两类执行，并记录父子关系、阶段、状态、耗时和安全摘要。
- 在聊天与 AIOps 执行入口创建 Trace，在 Agent 阶段、工具调用、完成和失败边界持续写入 Span，并保证异常路径也能终结 Trace。
- 扩展共享 HTTP/SSE 合同，使同一次执行的事件携带稳定 `traceId`，工具事件同时携带对应 `spanId`。
- 新增 Trace 列表与详情 API，支持按执行类型、状态和关联资源筛选，并强制按当前用户隔离。
- 新增桌面端“执行追踪”页面，以列表、摘要指标和有序 Span 时间线展示聊天与 AIOps 执行链路。
- 增加迁移、仓库、服务、API、SSE、权限与前端组件测试，并验证敏感参数不会进入 Trace 摘要。

## Capabilities

### New Capabilities

- `agent-execution-traces`: 定义统一 Trace/Span 生命周期、owner 范围查询、关联资源与桌面端可视化。

### Modified Capabilities

- `api-and-sse-contracts`: HTTP 与 SSE 合同增加稳定的 Agent Trace 上下文和 Trace 查询端点。
- `stream-rag-chat`: 每次聊天 Agent 执行创建并终结统一 Trace，并将工具生命周期映射为 Span。
- `aiops-diagnosis-tasks`: 每次 AIOps 后台诊断创建并终结统一 Trace，并将图阶段与工具生命周期映射为 Span。
- `request-observability`: 请求日志能够关联 Agent `traceId`，且不记录敏感输入和工具凭据。

## Impact

- 后端：`super_ai.tracing`、SQLite 模型/迁移/仓库、聊天流服务、AIOps 诊断服务、API 路由与响应序列化。
- 共享合同：`packages/api-contracts` 的 Trace 类型、SSE 类型与 OpenAPI 路径。
- 前端：受保护数据客户端、路由/导航、Trace 状态管理和桌面端详情视图。
- 数据：新增 owner 范围的 Trace 与 Span 表和索引；不依赖外部 SaaS，不存储模型密钥、完整提示词或原始工具凭据。
