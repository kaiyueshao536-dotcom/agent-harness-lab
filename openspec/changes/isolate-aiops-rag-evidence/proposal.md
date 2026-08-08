## Why

真实 `PaymentGatewayTimeoutHigh` 验收中，Planner 的 Top-3 检索同时返回 1 份正式 SOP 和 2 份历史 `diagnostic-case`，最终报告因此声称本次出现过并不存在的 MCP 失败和零结果。当前问题不是长对话 Token 截断，而是 AIOps 将规范性 SOP 与经验性历史案例放在同一检索通道、未使用已有 metadata filter，且没有可复盘的检索决策快照。

## What Changes

- 为知识文档上传和向量 chunk 增加受控检索元数据：`knowledgeType`、`incidentId`、`alertName`、`service`、`sopId`，并保持 owner/tenant 过滤不变。
- AIOps Planner 默认仅检索 `knowledgeType=sop`；历史 `diagnostic-case` 继续持久化和索引，但不再计入 SOP 命中，也不能作为当前执行事实。
- 基于告警中的 `sop`、`incident_id`、`alertName` 和 `service` 构造面向 SOP 的查询，并在没有正式 SOP 时明确回退为通用计划。
- 在 Planner step 中持久化检索 Context Snapshot，记录查询、过滤策略、选中来源、知识类型、分数和没有命中的原因，不记录完整 Prompt、密钥或原始凭据。
- 在 AIOps 执行链中展示紧凑的检索快照，使操作者能够区分“正式 SOP”“历史案例”和“当前工具证据”。
- 增加 P3.3 离线污染回归 fixture，要求正确 SOP 被选中，并禁止无本次 Trace 支撑的历史失败描述进入报告。
- 更新教程、README、变更日志和版本复盘，记录真实问题、修复边界与已知限制。

## Capabilities

### New Capabilities

- `aiops-context-snapshots`: 定义 AIOps Planner 检索决策的安全持久化、API 暴露和前端解释。
- `aiops-rag-quality-gates`: 定义可离线复现的 SOP 选择与历史污染回归 Gate。

### Modified Capabilities

- `knowledge-retrieval-tool`: 明确 metadata 过滤必须同时作用于向量与 BM25 召回，并在 AIOps 中按知识角色调用。
- `document-indexing-jobs`: 将受控文档检索元数据传播到每个向量 chunk，使过滤在重建索引后可用。
- `aiops-diagnosis-tasks`: 将 SOP-first 细化为 SOP-only 主通道，历史诊断案例不得作为当前事实或 SOP 命中。
- `automated-diagnosis-case-library`: 保留案例自动沉淀能力，同时明确其 `diagnostic-case` 角色和默认检索隔离。
- `aiops-diagnosis-ui`: 在持久化执行链中展示检索 Context Snapshot 和知识角色。

## Impact

- 后端：文档上传验证、索引元数据、AIOps Planner、诊断 step payload、离线评测 fixture 和测试。
- 前端与共享合同：AIOps Planner step 的检索快照展示；保持现有 API 向后兼容，不新增数据库表。
- 数据：已有文档不会自动修改；需要重新运行 SOP seed 或重建索引后才获得新增的精确元数据。`knowledgeType` 已存在，因此 SOP-only 过滤可立即隔离历史案例。
- 外部系统：普通测试不调用真实 CLS；人工验收可复用现有告警、SOP 和已保存 Trace，避免重复产生云端查询费用。
