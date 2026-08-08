## ADDED Requirements

### Requirement: Deterministic AIOps retrieval contamination gate
仓库 SHALL 提供离线 P3.3 评测 fixture，用确定性规则验证正确 SOP 选择和历史失败污染排除。

#### Scenario: Current execution succeeds without tool failures
- **WHEN** fixture 中当前 Trace、Knowledge Retrieval 和 SearchLog 都成功
- **THEN** Gate MUST 要求输出包含正确 alert、service 和 SOP 标识，并排除本次执行未发生的 MCP unavailable、零结果或其他历史失败描述。

#### Scenario: Fixture runs offline
- **WHEN** 开发者通过 CLI 执行 P3.3 fixture
- **THEN** 评测 MUST 不访问模型、MCP、CLS、Milvus 或生产数据库，并返回可解释的逐规则结果。
