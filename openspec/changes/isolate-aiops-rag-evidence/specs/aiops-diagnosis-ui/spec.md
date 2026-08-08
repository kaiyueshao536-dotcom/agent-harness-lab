## ADDED Requirements

### Requirement: Explainable AIOps retrieval context
AIOps 执行链 SHALL 为包含检索 Context Snapshot 的 Planner step 展示紧凑的知识路由说明。

#### Scenario: Planner selected SOP sources
- **WHEN** 选定诊断的 Planner step 包含 Context Snapshot
- **THEN** 前端 MUST 显示策略、知识类型过滤、命中数量以及每个来源的名称、角色和分数，MUST NOT 展示完整 chunk 正文。

#### Scenario: No SOP matched
- **WHEN** Snapshot 的 selected 为空并包含 fallback reason
- **THEN** 前端 MUST 显示“未命中正式 SOP”及安全回退原因。

#### Scenario: Old Planner step has no snapshot
- **WHEN** 历史任务的 Planner payload 不包含 Context Snapshot
- **THEN** 前端 MUST 保持现有执行链展示且 MUST NOT 显示错误占位内容。
