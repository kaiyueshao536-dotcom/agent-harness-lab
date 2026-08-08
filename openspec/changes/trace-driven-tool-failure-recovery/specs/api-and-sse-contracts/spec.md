## ADDED Requirements

### Requirement: AIOps responses expose the latest background job
AIOps 创建、列表、详情和证据链任务契约 SHALL 包含当前 owner/diagnostic resource 的最新 Background Job 或明确空值。

#### Scenario: Diagnostic has retry history
- **WHEN** user 读取已产生一个或多个 retry Job 的诊断
- **THEN** 响应 MUST 返回按创建时间最新的 Job，并包含 attempt、maxAttempts、status、error、retryOfJobId 和时间字段

#### Scenario: Diagnostic has no visible job
- **WHEN** owner 范围内不存在该诊断的 Background Job
- **THEN** 响应 MUST 返回空 backgroundJob 且不得从其他 owner 关联任务
