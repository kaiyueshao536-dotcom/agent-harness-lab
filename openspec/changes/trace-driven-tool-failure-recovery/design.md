## Context

当前 `LocalMcpClient` 已在单次调用内执行 `retries + 1` 次连接尝试，Background Job Repository 也已能从 failed/cancelled Job 创建带 `retry_of_job_id` 的新 Job。但 AIOps 创建时固定 `max_attempts=1`，历史/证据链响应不携带最新 Job，前端无法触发通用 retry API；同时 AIOps 在 LangGraph 节点返回后才把缓冲的 `tool.call` 事件映射为 Span，导致 779 ms 的真实 `SearchLog` 调用只显示为 33 ms，且内部 Attempt 完全不可见。

P3 涉及 MCP Client、AIOps Runner、Trace、后台任务 API、共享合同、Vue 状态和 Evaluation 工作台。实现必须保持 owner 隔离、安全错误摘要和当前 SQLite/同进程 Runtime 架构，不提交任何 CLS 凭据或原始日志。

## Goals / Non-Goals

**Goals:**

- 让一次逻辑 MCP 工具调用的父 Span 覆盖真实执行时间，并以子 Span 展示每次 Attempt。
- 让失败 AIOps 诊断从原任务页面创建关联新 Job，在同一资源下生成独立新 Trace，并恢复持久化 SSE 进度。
- 复用现有 Background Job retry、owner 过滤、状态约束和 `retry_of_job_id`，不建立平行重试系统。
- 让 Evaluation 页面能组合规则并选择失败 Trace，使用 P2 对失败与恢复 Trace 做负例/正例验证。
- 为错误分类、Attempt、状态一致性、权限和 UI 恢复增加确定性测试。

**Non-Goals:**

- 不引入 Celery、Redis、独立 Worker 或跨进程分布式调度。
- 不实现任意 LangGraph 节点断点续跑；任务重试从 Planner 重新执行。
- 不自动重试整个 AIOps Job；P3 只允许用户对 failed/cancelled Job 手动重试。
- 不为创建工单、删除资源等副作用工具建立通用幂等平台。
- 不在本版本处理 CLS 查询时间窗、通配符和成本预算问题。

## Decisions

### 复用 Background Job retry，并保持同一诊断资源

前端调用现有 `POST /background-jobs/{jobId}:retry`。Repository 创建新 Job，复制 kind、resource、payload、timeout 和尝试上限，写入 `retry_of_job_id`；诊断 ID 不变。Runner 每次实际执行仍调用 `start_trace`，因此恢复尝试获得新 Trace，而旧失败 Trace 永久保留。

替代方案是重新调用 `POST /aiops/diagnostics` 创建新诊断，但这会丢失重试关系并要求用户重复输入，因此不采用。另一个方案是把旧 Job 重新置为 queued，但会覆盖一次尝试的终态和审计，不采用。

### 最新 Job 成为 AIOps DTO 的服务器事实

创建、列表、详情和证据链中的诊断任务都携带 owner/resource 下最新 Background Job。前端不自行猜测 Job，也不从全局任务列表拼接。重试返回新 Job 后，前端立即更新活动任务并重新订阅同一诊断 SSE。

### 逻辑工具 Span 与 Attempt 子 Span 分层

Runner 在 Executor 真正调用工具前创建父 `tool` Span，在成功或失败后终结；Tool Audit 仍是一条逻辑工具调用记录。`LocalMcpClient.call_tool` 接受可选的 Attempt observer，在每次连接尝试开始和结束时回调安全事件。Runner 将其映射为 `attempt` 子 Span，属性只包含 attemptNumber、maxAttempts、connectionName 和 errorCategory。

Attempt 不使用 `tool` kind，避免 Evaluation 的工具调用数量和 Trace 工具数量被重试次数放大。原有缓冲 SSE `tool.call` 事件继续面向前端，但 Trace 映射检测到已由 Executor 终结的 Span 后只复用 spanId，不覆盖真实时间。

替代方案是只在父 Span 写 `attemptCount`，实现更简单但无法分析每次尝试耗时；另一方案是把 Trace Service 传进 MCP 基础设施层，会耦合可观测存储，因此采用中立 observer 回调。

### 有界指数退避与安全错误分类

MCP 的总尝试次数保持 `retries + 1`，等待时间使用小型有界指数退避。Attempt 只公开异常类名，最终调用仍抛出不含凭据、URL 查询参数或底层响应正文的 `McpClientError`。P3 不把所有异常都提升为业务级自动任务重试。

### Evaluation 通过真实负例验证恢复

Evaluation 工作台加载 owner 的成功和失败 Trace，并在选项中展示状态；Case Builder 支持暂存多条已有确定性规则。服务端评分逻辑不变。这样可以用失败 Trace 验证 `trace_succeeded`，再用恢复 Trace 验证同一规则和必需工具，而不调用模型或 CLS。

## Risks / Trade-offs

- [同一诊断重试会追加步骤、证据和报告] → 保留每次 Trace/Job 关系，UI 以最新 Job/最新报告为当前状态，历史记录不删除；本版本不拆分 attempt 级证据视图。
- [用户在 MCP 仍不可用时反复点击重试] → UI 在请求期间禁用按钮，Repository 只接受 failed/cancelled 源 Job；每次失败仍可审计。全局速率限制留到后续成本治理。
- [Attempt observer 自身写 Trace 失败] → 延续 Trace Service 的 failure-tolerant 语义，可观测写失败不得改变 MCP 业务结果。
- [增加 failed Trace 选择可能误绑错误执行类型] → UI 按 executionType 过滤，后端继续强制校验 owner 和执行类型。
- [同进程 Runtime 崩溃] → 沿用已有租约恢复；P3 不承诺独立 Worker 的可用性。

## Migration Plan

1. 扩展共享 Span kind 和 AIOps DTO；不修改数据库列类型，无 Alembic 迁移。
2. 增加 MCP Attempt observer、Executor 真实工具 Span 和相关测试。
3. 让 AIOps API 附带最新 Job并增加契约测试。
4. 增加前端重试和 Evaluation 负例能力。
5. 运行后端、合同、前端、OpenSpec 和 VitePress 验证，再执行一次本地 MCP 故障闭环。

回滚时可恢复应用代码和合同；已有 `attempt` Span 在 SQLite 中是普通字符串 kind，旧代码会回退显示为通用阶段或忽略，不影响 Trace 主记录。

## Open Questions

- P3 验收后再决定是否在 P4 增加 attempt 级证据/报告分组；当前只要求 Job/Trace/Span 可追溯。
- CLS 查询预算、24 小时通配符和调用成本门禁保留到 P5。
