## Why

真实 MCP 故障演练证明，AIOps 能记录 `SearchLog` 失败，却无法从页面重试原诊断、无法在 Trace 中看到每次连接 Attempt，且工具 Span 耗时不代表真实调用耗时。现在需要复用已有 Background Job retry 能力，建立从明确失败、依赖恢复、关联重试到 Trace/Evaluation 验证的最小恢复闭环。

## What Changes

- 为 MCP 工具调用增加有界 Attempt 生命周期与指数退避，按逻辑工具 Span 的子 `attempt` Span 记录次数、状态、真实耗时和安全错误类别。
- 修正 AIOps 工具 Span 的埋点边界，使父工具 Span 包裹真实调用，并保持 Tool Audit 与 Trace 可通过稳定工具调用 ID 关联。
- 复用 owner 范围的 Background Job retry API，为失败或取消的 AIOps 任务创建关联新 Job；同一诊断资源的每次实际执行创建独立 Trace。
- 在 AIOps 历史与证据链响应中返回最新 Background Job，在失败工作区提供明确的中文重试操作，并在重试期间重新订阅同一诊断的持久化 SSE 事件。
- 允许 Evaluation 工作台选择失败 Trace，并为同一 Case 组合多条确定性规则，以便用 `trace_succeeded`、必需工具和耗时规则验证失败与恢复结果。
- 增加故障注入、Attempt Trace、重试权限/状态、前端恢复交互和评测负例测试；不引入自动执行副作用工具、分布式 Worker 或任意节点断点恢复。

## Capabilities

### New Capabilities

- `trace-driven-tool-failure-recovery`: 定义外部工具 Attempt 可观测性、AIOps 关联重试、恢复交互和 Trace-backed 失败/恢复验证闭环。

### Modified Capabilities

- `real-mcp-tools`: MCP 调用在有限重试时公开每次安全 Attempt 结果并使用有界指数退避。
- `background-job-runtime`: 手动重试必须创建关联的新 Job、保留同一 owner/resource，并拒绝不合法状态或跨 owner 重试。
- `aiops-diagnosis-tasks`: 同一诊断资源的每次实际执行必须创建独立 Trace，并保留失败与恢复后的执行历史。
- `aiops-diagnosis-ui`: 失败诊断必须展示可操作的重试入口和重试中的真实进度，不再要求用户重新填写并创建无关联任务。
- `api-and-sse-contracts`: AIOps 任务响应必须携带最新 Background Job，使前端可以安全取消、重试和展示关联状态。

## Impact

- 后端：`super_ai.mcp_client`、`super_ai.aiops.diagnostics`、统一 Trace Service/SQLite 仓储、Background Job 与 AIOps API 序列化。
- 共享合同：Trace Span kind、AIOps 最新 Job、OpenAPI 与前端类型。
- 前端：AIOps client/store/report交互、Trace Attempt 展示、Evaluation Trace 选择与多规则 Case Builder。
- 测试：MCP 客户端、AIOps Runner、Trace、Background Job API、共享合同、Pinia store、Vue 组件与 Evaluation 工作台。
- 数据：不新增凭据字段；Attempt 只保存序号、状态、耗时、服务端白名单属性和安全错误类别。
