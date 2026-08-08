## ADDED Requirements

### Requirement: AIOps retry preserves diagnostic identity and execution history
每次 AIOps 恢复 Job SHALL 复用原诊断任务输入和资源 ID，从 Planner 重新执行，并创建独立 Trace、步骤、审计、证据和报告记录。

#### Scenario: Retried diagnostic starts
- **WHEN** Runtime 领取关联的 AIOps retry Job
- **THEN** 诊断任务 MUST 从失败/取消状态回到 running，Runner MUST 创建新 Trace，并 MUST NOT 删除原 Job、Trace 或失败证据

#### Scenario: Retried diagnostic finishes
- **WHEN** 恢复执行成功或再次失败
- **THEN** 最新 Job、诊断终态和新 Trace MUST 一致，历史 Job 与 Trace MUST 继续可查询
