## ADDED Requirements

### Requirement: AIOps execution produces unified trace
每次 AIOps 后台诊断实际执行 SHALL 创建一个关联当前 owner 和诊断任务的统一 Trace，并将 Planner、Executor、Replanner、Report 与工具生命周期映射为有序 Span。

#### Scenario: Diagnostic stages are traceable
- **WHEN** AIOps 图完成一次诊断
- **THEN** Trace 详情 MUST 按执行顺序包含阶段 Span，并终结为 `succeeded`

#### Scenario: Diagnostic execution fails
- **WHEN** AIOps 图或工具执行导致任务失败
- **THEN** Trace MUST 终结为 `failed`，并通过同一 `traceId` 关联错误 SSE 和结构化日志
