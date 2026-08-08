## MODIFIED Requirements

### Requirement: SOP-first diagnostic planning
在创建诊断计划之前，Planner SHALL 通过 tenant 授权且 `knowledgeType=sop` 的主检索通道检索正式 SOP；历史 `diagnostic-case` 不得计为 SOP 命中或当前事实。

#### Scenario: Matching SOP informs plan
- **WHEN** 角色过滤检索返回一个或多个 SOP 结果
- **THEN** 计划和报告 MUST 识别已检索到的正式 SOP，并可优先推荐其中的诊断操作。

#### Scenario: Historical case is semantically similar
- **WHEN** 同一知识库存在相关分较高的 `diagnostic-case`
- **THEN** Planner 主检索 MUST 排除该案例，MUST NOT 将案例内容、历史工具失败或历史结论写入当前计划事实。

#### Scenario: No SOP match is explicit
- **WHEN** SOP 角色过滤后没有任何结果
- **THEN** 诊断 SSE 生命周期和最终报告 MUST 明确指出没有 SOP 匹配，并且该计划是通用的，MUST NOT 使用历史案例冒充 SOP。

## ADDED Requirements

### Requirement: Alert-aware SOP retrieval query
Planner SHALL 使用当前诊断 query 和标准化告警中的可用 SOP、incident、alert 与 service 标识构造检索 query。

#### Scenario: External alert carries correlated identifiers
- **WHEN** 告警上下文包含 `sop`、`incident_id`、`alertName` 或 `service`
- **THEN** Planner 检索 query MUST 包含可用标识，并在 Context Snapshot 中保留这些非敏感路由字段。
