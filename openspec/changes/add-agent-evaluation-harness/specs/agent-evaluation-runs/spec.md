## ADDED Requirements

### Requirement: Trace-backed evaluation run
系统 SHALL 使用 owner 范围的真实 Agent Trace 作为案例观察来源，按案例批量解析业务结果和 Trace/Span 指标，并且不得接受客户端伪造的实际输出或性能指标。

#### Scenario: Chat trace is evaluated
- **WHEN** Chat 案例绑定一个当前 owner 的成功 Chat Trace
- **THEN** 系统 MUST 从关联会话读取最终助手结果，并从 Trace/Span 计算工具、引用、状态和耗时

#### Scenario: AIOps trace is evaluated
- **WHEN** AIOps 案例绑定一个当前 owner 的 AIOps Trace
- **THEN** 系统 MUST 从关联诊断任务读取最终报告，并从证据与 Span 计算引用、工具、状态和耗时

#### Scenario: Trace type mismatch
- **WHEN** 案例执行类型与绑定 Trace 的执行类型不同
- **THEN** 系统 MUST 拒绝该运行并返回明确业务错误

#### Scenario: Cross-owner trace is hidden
- **WHEN** 运行绑定另一个 owner 的 Trace
- **THEN** 系统 MUST 返回 404 且不得创建部分运行结果

### Requirement: Explainable deterministic scoring
系统 SHALL 对每条规则生成通过状态和安全说明，对每个案例生成 0 到 1 的分数，并以稳定算法聚合运行指标。

#### Scenario: All rules pass
- **WHEN** 观察结果满足案例全部规则
- **THEN** 案例 MUST 标记为通过、分数为 1，并保存每条规则的通过说明

#### Scenario: One rule fails
- **WHEN** 观察结果不满足至少一条规则
- **THEN** 案例 MUST 标记为失败，失败检查 MUST 指明规则类型但不得复制完整模型正文或原始工具输入

### Requirement: Quality gate and baseline comparison
每次完成的运行 SHALL 根据数据集门禁计算独立 gate 状态，并可与同数据集的 owner 范围基线运行比较质量与效率变化。

#### Scenario: Candidate meets gate
- **WHEN** 运行通过率和平均分达到阈值，且基线耗时回退未超过上限
- **THEN** gate MUST 标记为 `passed`

#### Scenario: Candidate regresses against baseline
- **WHEN** 候选运行平均耗时相对基线超过允许回退比例
- **THEN** gate MUST 标记为 `failed` 并返回耗时变化百分比

#### Scenario: Invalid baseline
- **WHEN** 基线运行属于其他 owner 或其他数据集
- **THEN** 系统 MUST 隐藏或拒绝该基线且不得创建运行

### Requirement: Safe persisted evaluation evidence
评测记录 SHALL 只持久化规则结果、长度受限的输出摘要、聚合指标和关联 Trace ID，MUST NOT 复制完整提示词、思维链、凭据或原始工具输入输出。

#### Scenario: Result contains sensitive business context
- **WHEN** 真实业务结果或 Trace 包含较长内容
- **THEN** 评测详情 MUST 只返回有界摘要和布尔检查结果，不得返回业务正文副本
