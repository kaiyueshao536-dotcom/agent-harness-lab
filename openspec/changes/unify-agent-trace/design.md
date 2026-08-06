## Context

系统已经有 HTTP `requestId`、聊天/AIOps 工具审计、AIOps 步骤与证据链、后台任务事件和共享 SSE 合同，但这些记录缺少统一根标识。聊天工具审计与 AIOps 工具审计虽然已经合并到 owner 范围的 `tool_call_audits`，仍只能从具体会话或诊断任务反查，无法得到一次 Agent 执行的完整阶段、耗时和失败位置。

本变更横跨 SQLite、服务层、共享合同和 Vue 桌面端。必须保持用户隔离、无明文秘密、无模块导入副作用，并兼容现有聊天与 AIOps SSE 消费方。

## Goals / Non-Goals

**Goals:**

- 用一个稳定 `traceId` 关联一次聊天或 AIOps Agent 执行的阶段、工具调用、完成与失败。
- 提供轻量、可测试、owner 范围的 Trace/Span 持久化和查询能力。
- 让共享 SSE、结构化日志、API 和桌面端使用相同 Trace 标识与状态语义。
- 为后续自动评测、性能回归和多 Agent 编排提供数据底座。

**Non-Goals:**

- 不接入 LangSmith、OpenTelemetry Collector、Jaeger 或其他外部可观测 SaaS。
- 不存储完整提示词、模型思维链、工具凭据或未经裁剪的工具输入输出。
- 不实现 Trace 自动评分、数据导出、跨服务分布式采样或长期归档策略。
- 不把业务日志中的 `trace_id` 与 Agent `traceId` 强行合并；前者作为工具/证据属性保留。

## Decisions

### 1. 使用独立 Trace/Span 表，而不是动态聚合现有审计表

新增 `agent_traces` 和 `agent_trace_spans`。Trace 保存执行类型、关联资源、状态、时间和摘要；Span 保存有序阶段、类型、父子关系、安全属性及耗时。

选择独立表是因为聊天消息、AIOps 步骤和工具审计的生命周期与字段并不一致，运行时动态 union 会造成状态推断、分页和权限过滤复杂。现有记录继续作为业务审计源，Span 只保存统一索引和安全摘要。

### 2. 通过显式服务边界写入，而不是全局 ContextVar 魔法

新增 `AgentTraceService`，依赖注入 `AgentTraceRepository`。聊天和 AIOps 服务在执行入口显式创建 Trace，在已存在的工具/阶段边界开始或终结 Span，并在 `try/except` 中终结 Trace。

显式依赖便于单元测试，也避免后台任务切换协程后丢失隐式上下文。`traceId` 通过 SSE 构造函数和结构化日志字段显式传递。

### 3. Trace 是执行根，Span 使用有序扁平时间线并保留可选父 ID

每个 Trace 本身代表一次 Agent run，不额外创建冗余根 Span。Span 具有单调递增 `sequence`、可选 `parentSpanId`、`kind`、`name`、`status`、开始/结束时间和安全属性。前端默认按 sequence 展示，同时可根据父 ID 缩进。

相较只存树结构，sequence 能稳定还原 SSE 顺序；相较只存平面事件，可选父 ID 仍能表达工具属于 Executor 等关系。

### 4. 统一状态和标识格式

- Trace：`running | succeeded | failed`。
- Span：`running | succeeded | failed`。
- 执行类型：`chat | aiops`。
- Span 类型：`agent | planner | executor | replanner | tool | retrieval | model | report`。
- 标识：`trace_<uuid hex>` 与 `span_<uuid hex>`。

工具事件使用工具调用 ID 作为关联属性，但 Span 使用独立 ID，避免第三方 run ID 冲突。

### 5. 默认只持久化安全摘要

Trace/Span 属性只接受由服务端构造的白名单字段，例如工具名、步骤序号、引用数量、错误类别和关联 ID。文本摘要限制长度，错误只记录类型化安全消息；不直接持久化提示词、模型正文、tool input/output 或密钥字段。

### 6. API 使用 owner 范围查询，404 隐藏跨用户资源

新增 `GET /agent-traces` 和 `GET /agent-traces/{traceId}`。列表支持 `executionType`、`status`、`resourceType`、`resourceId` 和受限 `limit`；详情返回 Trace 与有序 Span。仓库查询始终要求 `owner_user_id`，跨用户详情返回 404。

### 7. 前端采用桌面双栏主从视图

新增“执行追踪”导航和页面。左侧显示可筛选 Trace 列表，右侧显示总耗时、Span/工具数量、状态、关联资源及按时间排序的阶段链。状态和技术标识使用语义标签，不新增移动端专用交互。

## Risks / Trade-offs

- [双写可能失败，业务执行仍成功] → Trace 写入采用明确错误边界；创建失败时不阻断 Agent，测试验证降级行为，结构化日志记录追踪写入故障。
- [Span 数量增长] → 本阶段只记录阶段与工具生命周期，不记录逐字符 token/SSE delta；列表限制最大条数并建立 owner/时间索引。
- [后台任务重试产生多次执行] → 每次实际 run 创建独立 Trace，`resourceId` 仍指向同一诊断任务，便于比较重试。
- [工具调用与 Span 双份数据] → 工具审计保留安全输入与结果摘要，Span 仅保留关联 ID 和阶段耗时；两者职责不同。
- [旧执行没有 Trace] → 不回填历史数据；API 和 UI 仅展示变更上线后的执行。

## Migration Plan

1. 增加表与索引，不修改现有表，迁移可独立回滚。
2. 上线仓库与 Trace 服务，再接入聊天和 AIOps 执行写入。
3. 上线共享合同、查询 API 和前端视图。
4. 验证新旧 SSE 消费、owner 隔离、失败终结和无秘密记录。
5. 回滚时先停止新写入和隐藏前端入口，再回退 API；必要时删除新增表，不影响原业务记录。

## Open Questions

- Trace 保留周期和归档策略留到 Evaluation Harness 阶段结合数据规模决定。
- 是否映射为 OpenTelemetry Trace/Span 留到需要跨进程或外部 Collector 时决定。
