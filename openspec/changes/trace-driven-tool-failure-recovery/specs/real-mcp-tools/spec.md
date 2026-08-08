## ADDED Requirements

### Requirement: Observable bounded MCP attempts
MCP Client SHALL 对每次工具连接尝试发出安全的 started/succeeded/failed Attempt 生命周期，并在配置的有限次数内使用有界指数退避。

#### Scenario: Configured retries are attempted
- **WHEN** MCP connection 的 `retries` 为 1 且首次连接失败
- **THEN** Client MUST 最多执行首次尝试和一次重试，并 MUST 为两次 Attempt 分别产生状态与耗时

#### Scenario: Attempt error contains sensitive upstream data
- **WHEN** 底层 MCP 异常包含凭据、请求正文或上游响应
- **THEN** observer、Trace 和结构化日志 MUST 只公开安全异常类别与白名单连接名称
