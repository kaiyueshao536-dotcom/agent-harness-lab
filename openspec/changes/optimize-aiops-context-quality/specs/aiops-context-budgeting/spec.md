## ADDED Requirements

### Requirement: Metadata-aware SOP context selection
AIOps Planner SHALL 在正式 SOP 角色过滤后，根据当前告警名称和服务 metadata 选择上下文，并 MUST 排除与当前路由字段明确冲突的候选。

#### Scenario: Candidate belongs to another service
- **WHEN** 当前告警服务为 `payment-service`，SOP 候选明确声明 `service=search-service`
- **THEN** Planner MUST 将该候选标记为 `metadata-conflict` 且不得把其正文放入计划上下文

#### Scenario: Legacy SOP lacks routing metadata
- **WHEN** SOP 候选没有 alert/service 路由字段且知识角色为 `sop`
- **THEN** Planner MUST 将其作为 `generic` 候选参与预算选择，而不得假装其与当前告警精确匹配

### Requirement: Bounded SOP prompt context
Planner SHALL 对进入计划模型的 SOP 正文执行固定的近似 Token 预算，预算 MUST 在模型调用前生效。

#### Scenario: Candidates exceed budget
- **WHEN** 按相关性排序的 SOP 正文总量超过配置预算
- **THEN** Planner MUST 按优先级截断或排除超额内容，并记录实际使用量和排除原因

#### Scenario: No relevant SOP remains
- **WHEN** 所有带路由 metadata 的 SOP 均与当前告警冲突且没有 generic 候选
- **THEN** Planner MUST 使用现有通用证据收集计划，并明确记录无合格 SOP 的退化原因
