## ADDED Requirements

### Requirement: Versioned Chat memory evaluation dataset
系统 SHALL 支持 owner-scoped、版本化的 Chat memory Dataset，Case MUST 能声明压缩前消息、复核提示、预期当前约束、预期已废止值和故障注入类型。

#### Scenario: User defines a retention case
- **WHEN** user 创建关键约束保留 Case 并发布 Dataset 版本
- **THEN** 版本 MUST 固化输入消息、精确预期值和确定性评分规则

### Requirement: Deterministic memory scoring
Chat memory 评测 SHALL 从结构化快照、Trace 和持久化 assistant message 确定性计算约束保留、旧值泄漏、无来源事实、重复输出、压缩成功和耗时指标，MUST NOT 使用 LLM 自评这些规则。

#### Scenario: Current constraint is missing
- **WHEN** 预期 active value 不存在于快照或复核回答
- **THEN** constraint retention 规则 MUST 失败并指出缺失的 Case 字段

#### Scenario: Superseded value leaks into current answer
- **WHEN** 已废止值出现在要求仅回答当前事实的 assistant message
- **THEN** superseded leakage 规则 MUST 失败

#### Scenario: Answer content is duplicated
- **WHEN** 最终回答包含连续重复的完整答案
- **THEN** duplicate output 规则 MUST 失败

### Requirement: Chat memory quality Gate
评测运行 SHALL 聚合 Case 的约束保留率、旧值泄漏率、无来源事实数、重复输出数、压缩成功率和耗时，并与 Baseline 及 Gate 阈值比较。

#### Scenario: Candidate preserves quality
- **WHEN** 所有必需 Case 通过且聚合指标未突破 Gate 阈值
- **THEN** 运行 MUST 标记 Gate 通过并保存可复查的 Case 结果

#### Scenario: Compression reliability regresses
- **WHEN** 候选版本的压缩成功率下降或耗时回归超过阈值
- **THEN** Gate MUST 失败，即使部分最终回答文本仍然正确
