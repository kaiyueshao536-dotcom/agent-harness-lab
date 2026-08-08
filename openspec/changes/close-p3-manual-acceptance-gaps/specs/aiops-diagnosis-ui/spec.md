## ADDED Requirements

### Requirement: 失败诊断的降级报告与恢复操作并存
AIOps 工作区 SHALL 允许失败任务同时展示已生成的降级报告和关联重试入口，并 SHALL 以失败语义标记该报告。

#### Scenario: 失败任务已经生成降级报告
- **WHEN** 所选诊断状态为 failed、最新 Background Job 可重试且存在持久化报告
- **THEN** 页面 MUST 展示“失败后的降级报告”和“重试本次诊断”按钮

#### Scenario: 失败任务没有报告
- **WHEN** 所选诊断状态为 failed、最新 Background Job 可重试且不存在报告
- **THEN** 页面 MUST 展示失败说明和“重试本次诊断”按钮

#### Scenario: 成功任务包含报告
- **WHEN** 所选诊断状态为 succeeded 且存在报告
- **THEN** 页面 MUST 使用成功状态展示报告，MUST NOT 展示失败重试动作
