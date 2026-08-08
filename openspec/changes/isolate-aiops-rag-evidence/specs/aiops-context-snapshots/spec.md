## ADDED Requirements

### Requirement: Persisted AIOps retrieval context snapshot
系统 SHALL 为每次 AIOps Planner 知识检索持久化安全的 Context Snapshot，说明实际查询、过滤策略和最终选中来源。

#### Scenario: Planner selects SOP hits
- **WHEN** Planner 的角色过滤检索返回一个或多个 SOP
- **THEN** Planner step payload MUST 保存策略名、查询、metadata filter、允许和排除的知识类型，以及每个选中来源的 document ID、source、knowledge type 和最终分数。

#### Scenario: Planner finds no SOP
- **WHEN** 角色过滤检索没有返回 SOP
- **THEN** Snapshot MUST 保存空的 selected 列表和安全 fallback reason，且 MUST NOT 声称历史案例是 SOP。

#### Scenario: Snapshot remains safe
- **WHEN** Snapshot 通过证据链 API 返回
- **THEN** 它 MUST NOT 包含完整 Prompt、完整 chunk 正文、模型思维链、凭据、MCP URL 或 CLS Topic ID。

### Requirement: Backward-compatible snapshot exposure
系统 SHALL 通过现有诊断 step payload 暴露 Context Snapshot，不要求数据库迁移。

#### Scenario: Older task has no snapshot
- **WHEN** 用户打开 P3.3 之前创建的诊断任务
- **THEN** API 和前端 MUST 继续展示原执行链，不得因缺少 Snapshot 失败。
