## ADDED Requirements

### Requirement: Safe context quality snapshot
每次 Planner SOP 选择 SHALL 持久化安全的 Context Snapshot，区分检索候选与实际进入上下文的来源，并说明预算和决策原因。

#### Scenario: Relevant and irrelevant SOPs coexist
- **WHEN** 检索同时返回当前服务 SOP 与其他服务 SOP
- **THEN** Snapshot MUST 展示候选来源、选中或排除决策、原因、估算 Token 和总预算，且不得保存完整正文或 Prompt

#### Scenario: Older snapshot is displayed
- **WHEN** 历史 Planner step 只有 `sop-only` Snapshot
- **THEN** 桌面执行链 MUST 保持原有展示，不得因缺少 P4 字段而报错

### Requirement: Context quality explanation in desktop UI
桌面 AIOps 执行链 SHALL 用紧凑中文摘要展示上下文策略、预算用量、选中来源和排除来源。

#### Scenario: Source excluded by service conflict
- **WHEN** Snapshot 将 SOP 标记为 `metadata-conflict`
- **THEN** 页面 MUST 显示该来源未进入 Planner 以及对应服务冲突原因
