## ADDED Requirements

### Requirement: Trace 时间线展示可理解的父子执行关系
Agent Trace 工作台 SHALL 使用已持久化的 `parentSpanId` 展示 Span 层级，并 SHALL 在不改变 sequence 执行顺序的前提下显示安全的 Attempt 次数信息。

#### Scenario: Tool 包含两次失败 Attempt
- **WHEN** 一个 Tool Span 包含两个带有 `attemptNumber` 和 `maxAttempts` 的子 Attempt Span
- **THEN** 时间线 MUST 将两个 Attempt 缩进到该 Tool 下，并分别显示“第 1/2 次尝试”和“第 2/2 次尝试”

#### Scenario: Span 父节点缺失或形成循环
- **WHEN** Span 的 `parentSpanId` 无法解析或父链形成循环
- **THEN** 时间线 MUST 安全回退到根层展示，MUST NOT 阻断整个 Trace 页面

#### Scenario: Attempt 包含内部属性
- **WHEN** Attempt attributes 同时包含安全次数字段和其他内部字段
- **THEN** 前端 MUST 只展示白名单次数与错误类别，MUST NOT 展示任意原始 attributes JSON
