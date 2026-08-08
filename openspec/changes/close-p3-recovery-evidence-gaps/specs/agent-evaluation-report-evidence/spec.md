## ADDED Requirements

### Requirement: 确定性评测证据不足报告
自动评测 SHALL 提供可离线运行的 `evidence_cautious` 规则，在报告出现日志零结果信号时检查谨慎结论，并 SHALL 给出可解释的期望值与实际命中项。

#### Scenario: 零结果且谨慎陈述
- **WHEN** 已保存报告说明当前查询没有匹配日志、证据不足且无法确认原因
- **THEN** `evidence_cautious` MUST 通过，并 MUST 在 Rule Check 中说明已满足谨慎结论要求

#### Scenario: 零结果却断言采集链路异常
- **WHEN** 已保存报告同时包含零结果信号和“表明采集链路异常”等确定性推断
- **THEN** `evidence_cautious` MUST 失败，并 MUST 列出命中的过度推断模式

#### Scenario: 离线 CLI 使用相同规则
- **WHEN** 离线 CLI 对相同 Observation 和 Dataset 规则评分
- **THEN** CLI 与服务评分内核 MUST 返回相同的通过状态、分数和 Rule Check

### Requirement: Dataset 显式声明历史污染词
P3.2 回归 Dataset SHALL 使用 `excludes_all` 声明当前 Case 不允许出现的历史案例症状，并结合 Trace 成功、必需工具和谨慎证据规则形成质量门禁。

#### Scenario: 报告混入已知历史症状
- **WHEN** 当前 CLS 连通性 Case 的报告包含 Dataset 声明排除的“结算服务 API 延迟升高”
- **THEN** Case MUST 因 `excludes_all` 失败，且 Gate MUST 根据 Dataset 阈值失败

#### Scenario: 修复后的恢复 Trace
- **WHEN** 恢复后的 AIOps Trace 成功、调用 SearchLog、报告保持谨慎且不包含历史污染词
- **THEN** Case MUST 通过全部规则，并纳入 Baseline 与 Gate 聚合指标
