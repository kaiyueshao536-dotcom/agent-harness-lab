## Context

P3.2 已将历史案例正文从 Report 的直接事实上下文移除，但真实告警验收仍出现历史失败描述。只读审计证明当前 Trace 的 `knowledge_retrieval` 与 `SearchLog` 均成功；Planner 的三条检索命中却包含 1 条 `sop` 和 2 条 `diagnostic-case`。历史内容在 Planner 生成计划之前已经进入模型上下文，单靠 Report Prompt 的证据声明无法构成可靠隔离。

当前检索工具已经支持 `KnowledgeRetrievalFilters.metadata`，索引 chunk 也已有 `knowledgeType`，因此不需要新向量库或新检索框架。缺口在于 AIOps 没有使用角色过滤、用户上传的 SOP 缺少更细粒度的结构化元数据，以及 Planner step 没有记录检索策略和选中来源。

## Goals / Non-Goals

**Goals:**

- 正式 SOP、历史诊断案例和当前执行证据具有明确且不可混用的角色。
- AIOps Planner 的主检索通道只返回 `knowledgeType=sop`。
- Java 电商 SOP 的 incident、告警、服务和 SOP 标识进入文档及向量 chunk 元数据。
- 每次 Planner 检索都留下安全、可解释的 Context Snapshot。
- 用离线 Dataset 固化本次真实污染语句，防止同类回归。

**Non-Goals:**

- 不实现通用多级记忆平台、LLM Judge 或跨 Agent 共享记忆。
- 不拆分新的 Milvus Collection，不引入数据库迁移。
- 不自动相信历史成功报告；历史案例仍只用于案例库展示和未来显式的相似案例功能。
- 不在自动化测试中重复调用真实 CLS、MCP 或付费模型。

## Decisions

### 1. 使用知识角色过滤，而不是相关分阈值

Planner 调用现有检索工具时固定传入 `metadata={"knowledgeType": "sop"}`。相关分数只表达语义相似度，不能表达“能否作为规范性知识”；因此不使用一个经验阈值排除历史案例。

备选方案是将 SOP 和案例拆到两个 Collection。该方案会增加迁移、权限过滤和运维复杂度，当前单用户知识库规模不需要。

### 2. 通过受控上传元数据补充精确路由字段

文档上传接受一个可选 JSON 表单字段，只允许 `knowledgeType`、`incidentId`、`alertName`、`service` 和 `sopId`。`knowledgeType` 只允许 `document` 或 `sop`，不能由普通上传伪造 `diagnostic-case`。索引器将这些 allowlist 字段复制到 chunk metadata；owner、tenant、知识库和文档标识仍由服务器生成。

Java 电商 seed 脚本为每份 SOP 提交上述字段。AIOps 查询首先使用角色过滤；alert/service/sopId 进入查询文本和 Snapshot，为后续精确过滤保留数据基础。本阶段不要求所有历史用户文档都具备完整字段。

### 3. Context Snapshot 复用 Planner step payload

Snapshot 保存：查询、metadata filter、策略名、允许/排除的知识角色、选中命中的 document/source/type/score，以及 fallback reason。它不保存完整 Prompt、完整 chunk 正文、模型思维链或凭据。

该结构持久化在现有 `aiops_diagnostic_steps.payload` 中，通过已有证据链 API 返回，避免新增表。前端从 Planner payload 渲染紧凑卡片；旧任务没有 Snapshot 时维持原展示。

### 4. 历史案例默认不参与 Planner

自动案例继续以 `knowledgeType=diagnostic-case` 索引，支持案例库查看和未来的显式相似案例检索，但当前 Planner 不执行第二条历史案例检索。这样优先保证事实精度，代价是暂时放弃历史经验召回率。

### 5. Gate 使用确定性规则和安全 fixture

P3.3 fixture 组合现有 `contains_all`、`excludes_all`、`required_tools` 和成功 Trace 规则：必须出现正确告警/SOP/服务，且在当前工具均成功时不得出现 `MCP server unavailable`、`recordCount=0` 等历史失败词。fixture 不包含真实凭据或 Topic ID。

## Risks / Trade-offs

- [旧 SOP 没有精确元数据] → `knowledgeType=sop` 已能立即隔离案例；教程要求重新 seed 或重建索引以获得 incident/service 字段。
- [只检索 SOP 会降低历史经验召回] → P3.3 优先保证当前事实正确；未来若引入相似案例，必须走独立通道并标记为 hypothesis。
- [用户错误标记普通文档为 SOP] → 上传接口使用 allowlist 和长度/类型验证，但内容真实性仍需人工治理；Snapshot 使来源可复盘。
- [Snapshot 增加 step payload 大小] → 仅保存最多 3 条命中的有限字段和分数，不保存正文。
- [Prompt 仍可能无视边界] → 通过检索前隔离和离线污染 Gate 双重防护，不把 Prompt 当成唯一控制面。

## Migration Plan

1. 发布兼容的上传元数据、索引传播、Planner 过滤和 Snapshot 代码。
2. 重新运行 Java 电商 SOP seed；overwrite 会创建新文档并重新索引。
3. 使用离线 P3.3 fixture 验证污染 Gate，再进行一次显式真实告警人工验收。
4. 回滚时恢复应用代码即可；新增 metadata 和 Planner payload 字段会被旧代码忽略。

## Open Questions

- P4 是否增加独立的历史案例检索通道和 Token 预算 A/B；P3.3 不提前实现。
- 是否为普通用户上传提供图形化 metadata 编辑器；当前 seed/API 能力足以完成验收。
