## ADDED Requirements

### Requirement: 诊断任务按执行展示累计历史
AIOps 工作区 SHALL 将同一诊断任务的跨重试累计记录按独立 Trace 执行分组展示，并 MUST 明确区分任务累计工具调用数与单次执行工具调用数。

#### Scenario: 失败两次后恢复成功
- **WHEN** 一个诊断任务包含两条失败 Trace 和一条成功 Trace，每条 Trace 均包含两个逻辑工具调用
- **THEN** 页面 MUST 标注“跨 3 次执行累计 6 次工具调用”，并 MUST 为每个执行分组分别展示 Trace ID、状态、耗时和 2 次工具调用

#### Scenario: 只有一次执行
- **WHEN** 一个诊断任务只有一条 Trace
- **THEN** 页面 MUST 展示一次执行及其工具调用，MUST NOT 使用会暗示跨重试累计的文案

#### Scenario: 历史记录无法归属已有 Trace
- **WHEN** 旧数据中的步骤或工具审计无法落入任一 Trace 时间边界
- **THEN** 页面 MUST 将其保留在“未归属历史记录”分组，MUST NOT 丢弃或并入某条 Trace
