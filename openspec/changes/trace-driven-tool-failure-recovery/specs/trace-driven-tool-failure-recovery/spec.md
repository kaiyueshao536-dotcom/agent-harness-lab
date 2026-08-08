## ADDED Requirements

### Requirement: Trace-driven tool attempt lifecycle
系统 SHALL 为一次逻辑外部工具调用保留一个父工具 Span，并为每次有限连接 Attempt 保留有序子 Span，使失败、退避和最终恢复可以从同一 Trace 解释。

#### Scenario: First MCP attempt fails and retry succeeds
- **WHEN** MCP 工具首次连接失败且下一次有限重试成功
- **THEN** Trace MUST 包含一个 succeeded 父工具 Span、一个 failed Attempt 子 Span 和一个 succeeded Attempt 子 Span，并记录各自非负耗时

#### Scenario: All MCP attempts fail
- **WHEN** MCP 工具耗尽配置的有限尝试
- **THEN** 父工具 Span 和所有 Attempt 子 Span MUST 进入 failed，Trace MUST 只保留安全错误类别且不得包含凭据或原始上游响应

### Requirement: Owner-scoped diagnostic recovery chain
系统 SHALL 允许 owner 从 failed/cancelled AIOps Job 创建关联恢复 Job，并 SHALL 为每次实际执行创建独立 Trace，同时保留原失败 Job 和 Trace。

#### Scenario: Dependency recovers before manual retry
- **WHEN** owner 在 MCP 恢复后重试失败的 AIOps Job
- **THEN** 系统 MUST 创建带 `retryOfJobId` 的新 Job、复用原诊断资源、生成新 Trace，并在成功后保留失败与恢复两次执行

#### Scenario: User retries another owner's job
- **WHEN** user 请求重试不属于自己的 Job
- **THEN** API MUST 返回统一权限错误且不得泄露源 Job 或诊断信息

### Requirement: Trace-backed recovery evaluation
Evaluation 工作台 SHALL 能用确定性多规则 Case 分别评测失败和恢复 Trace，且不得重新调用模型或外部工具。

#### Scenario: Failed tool trace is a negative example
- **WHEN** user 为包含 `trace_succeeded` 和必需工具规则的 Case 绑定 owner 范围的 failed AIOps Trace
- **THEN** 运行 MUST 保留工具规则结果并因 Trace 状态规则失败而触发相应 Case/Gate 结果

#### Scenario: Recovered trace passes the same case
- **WHEN** user 将同一 Case 绑定到恢复后的 succeeded AIOps Trace
- **THEN** 运行 MUST 使用相同规则确定性评分并允许与先前运行比较
