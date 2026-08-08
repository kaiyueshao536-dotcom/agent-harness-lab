## ADDED Requirements

### Requirement: Deterministic context quality rule catalog
Evaluation Harness SHALL 支持封闭、可解释的上下文来源和预算规则，不得执行用户表达式或外部模型 Judge。

#### Scenario: P4 context passes all rules
- **WHEN** AIOps Trace 包含必需支付 SOP、不包含搜索 ES SOP且上下文 Token 不超过阈值
- **THEN** `required_context_sources`、`excluded_context_sources` 和 `max_context_tokens` MUST 全部通过

#### Scenario: Irrelevant source enters context
- **WHEN** Planner Snapshot 的实际选中来源包含 Dataset 禁止的 SOP
- **THEN** `excluded_context_sources` MUST 失败并列出命中的来源

### Requirement: Trace-backed context observation
真实 Evaluation Run SHALL 从 owner 范围内的 AIOps Planner step 提取实际选中来源和 Token 用量；CLI SHALL 使用同结构 fixture 调用相同评分内核。

#### Scenario: Legacy trace lacks P4 snapshot
- **WHEN** Dataset 对不含 P4 Snapshot 的旧 Trace 执行上下文预算规则
- **THEN** 规则 MUST 给出可解释失败，不得伪造 0 Token 为通过

#### Scenario: Offline P4 fixture
- **WHEN** CI 运行无密钥 P4 fixture
- **THEN** CLI MUST 不连接模型、Milvus、MCP 或 CLS，并根据同一上下文规则返回 Gate 退出码
