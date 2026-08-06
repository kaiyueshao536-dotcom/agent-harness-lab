## ADDED Requirements

### Requirement: Agent logs include trace correlation
Agent 执行结构化日志 SHALL 包含统一 `traceId`、执行类型和关联资源 ID，并继续遵守敏感字段禁止记录规则。

#### Scenario: Agent completion is logged
- **WHEN** 聊天或 AIOps Agent 执行完成或失败
- **THEN** 对应结构化日志 MUST 包含与 SSE 和查询 API 一致的 `traceId`

#### Scenario: Trace write failure is logged safely
- **WHEN** Trace 持久化自身失败
- **THEN** 系统 MUST 记录错误类别和关联资源，MUST NOT 记录提示词、工具参数或凭据
