## ADDED Requirements

### Requirement: Failed diagnosis recovery action
AIOps 工作区 SHALL 为带 failed/cancelled 最新 Job 的当前用户诊断展示明确中文重试操作，并在操作后继续展示同一诊断的真实持久化进度。

#### Scenario: Operator retries a failed diagnosis
- **WHEN** operator 在失败诊断上点击重试
- **THEN** 前端 MUST 调用 Background Job retry API、禁用重复提交、展示 queued/running 状态并重新订阅同一诊断 SSE

#### Scenario: Retry request is rejected
- **WHEN** 后端因权限、状态冲突或系统错误拒绝重试
- **THEN** 前端 MUST 显示安全中文错误、保留原失败证据且不得伪造运行中状态
