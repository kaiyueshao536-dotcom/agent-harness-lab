## ADDED Requirements

### Requirement: Chat execution produces unified trace
每次通过流式聊天端点启动的有效 Agent 执行 SHALL 创建一个关联当前 owner 和聊天会话的统一 Trace，并将工具生命周期写入该 Trace 的 Span。

#### Scenario: Chat stream succeeds
- **WHEN** Agent 生成最终助手消息
- **THEN** 所有聊天 SSE 事件 MUST 共享同一 `traceId`，对应 Trace MUST 终结为 `succeeded`

#### Scenario: Chat stream fails
- **WHEN** Agent runner 或持久化流程抛出异常
- **THEN** 错误 SSE MUST 携带该 `traceId`，对应 Trace MUST 终结为 `failed`
