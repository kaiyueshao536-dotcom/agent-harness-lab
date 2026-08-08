## ADDED Requirements

### Requirement: Historical case knowledge-role isolation
自动诊断案例 SHALL 始终使用服务器控制的 `diagnostic-case` 知识角色，并与 AIOps 正式 SOP 主检索隔离。

#### Scenario: Successful diagnosis becomes a case
- **WHEN** 成功报告被沉淀为知识文档和向量 chunks
- **THEN** 文档及每个 chunk MUST 包含 `knowledgeType=diagnostic-case`、来源任务标识和可用 alert/service 字段。

#### Scenario: Planner searches for SOP
- **WHEN** Planner 执行默认 SOP 主检索
- **THEN** 自动案例 MUST NOT 出现在检索结果、SOP 命中、当前执行证据或报告事实中。
