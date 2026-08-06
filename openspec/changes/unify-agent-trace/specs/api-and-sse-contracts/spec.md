## ADDED Requirements

### Requirement: Shared Agent trace contracts
共享 API-contract 包 SHALL 定义 Agent Trace 摘要、详情、Span、列表筛选和响应类型，并在 OpenAPI 中声明经过身份验证的 Trace 列表与详情端点。

#### Scenario: Contract package exposes trace API
- **WHEN** 前端或后端检查共享合同
- **THEN** 它 MUST 找到 `GET /agent-traces`、`GET /agent-traces/{traceId}` 及对应 Trace/Span schema

### Requirement: Agent SSE carries trace context
聊天和 AIOps Agent SSE 事件 SHALL 携带同一次执行稳定一致的 `traceId`，工具调用事件 SHALL 额外携带对应 `spanId`。

#### Scenario: Stream events are correlated
- **WHEN** 一个 Agent stream 发出多个阶段、工具、完成或错误事件
- **THEN** 所有事件 MUST 具有同一个非空 `traceId`

#### Scenario: Tool event links to span
- **WHEN** SSE 发出 `tool.call` 生命周期事件
- **THEN** 事件 MUST 包含可用于 Trace 详情查询的 `spanId`
