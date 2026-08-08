## ADDED Requirements

### Requirement: Linked manual background job retry
Background Job Repository SHALL 只允许 owner 对 failed/cancelled Job 创建新的关联 Job，并保留 kind、resource、payload、timeout、最大尝试次数和源 Job ID。

#### Scenario: Failed job is retried
- **WHEN** owner 重试自己的 failed Job
- **THEN** API MUST 返回 202 和新的 queued Job，新 Job MUST 使用新 ID并设置 `retryOfJobId` 为源 Job ID

#### Scenario: Non-terminal job is retried
- **WHEN** owner 尝试重试 queued、running 或 succeeded Job
- **THEN** API MUST 返回业务冲突且不得创建新 Job
