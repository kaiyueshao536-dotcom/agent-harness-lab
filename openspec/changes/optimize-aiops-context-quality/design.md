## Context

P3.3 将 Planner 检索限制为 `knowledgeType=sop`，真实支付告警命中三份 SOP：支付网关超时、网关熔断、搜索 ES 超时。第三份虽然语义分数为 `0.6540`，但元数据服务与当前 `payment-service` 不一致，仍占用 Prompt 并可能干扰计划。当前 Planner 固定 `top_k=3`，`sop_hits` 全量进入计划模型；Snapshot 只展示选中来源和分数，没有候选决策或 Token 预算。

## Goals / Non-Goals

**Goals:**

- 用可解释的告警/服务元数据亲和度排除明确冲突的 SOP。
- 对实际进入 Planner 的 SOP 正文实施 1,600 Token 总预算，并记录预算使用。
- 让候选、选中、排除原因可审计且不泄露正文。
- 让 P2 Evaluation 能对上下文来源与 Token 用量设确定性 Gate。
- 用同一批候选证明 P4 相比 P3.3 减少无关来源和上下文体量。

**Non-Goals:**

- 不实现通用长期记忆、跨 Agent 共享记忆或 LLM Judge。
- 不用单一相似度阈值判断业务相关性。
- 不新增向量库、数据库迁移或外部依赖。
- 不声称近似 Token 计数等同模型供应商账单 Token。

## Decisions

### 1. 角色过滤之后增加确定性元数据亲和度

Planner 先保持 `knowledgeType=sop`，再按候选 metadata 与当前告警身份分层：

1. `alert-match`：`alertName` 与当前告警一致；
2. `service-match`：`service` 与当前服务一致；
3. `generic`：候选缺少 alert/service 路由字段，保留兼容性；
4. `metadata-conflict`：候选显式声明了路由字段但均与当前上下文冲突，排除。

同层保持 Rerank 顺序。支付超时与熔断 SOP 可因告警/服务匹配保留，搜索 ES SOP 因服务冲突排除。相比再调一个分数阈值，该规则能解释业务边界，且不会把高相关的错误服务文档误当当前规范。

### 2. 预算只约束进入 Planner 的正文，不改变检索工具结果

检索 `top_k` 提升到 5，以便在过滤后仍有候选；Tool Audit 保存真实检索输出。选择器按优先级累计 SOP 正文，最大 1,600 近似 Token、最多 3 个来源。若首个合格来源超预算，安全截断正文以保证至少一份有限上下文；后续来源超预算则标记 `budget-exceeded` 并排除。

Token 使用复用 LangChain 已有近似计数工具，只用于策略比较和 Gate，不作为供应商账单依据。

### 3. Snapshot 分离候选与实际上下文

Snapshot 策略升级为 `sop-budget-v1`，保留旧 `sop-only` 兼容。每个候选只保存 documentId、source、knowledgeType、score、metadata affinity、decision、reason、estimatedTokens；预算保存 limit/used/truncated。完整 chunk、Prompt、凭据和 Topic ID 不进入 Snapshot。

### 4. Evaluation 从持久化 Planner step 提取上下文观察值

`EvaluationObservation` 增加 `context_source_names` 和 `context_tokens`。真实 AIOps Trace 通过关联诊断任务的 Planner step 解析最终一次 `retrievalContext`；Chat 或旧 Trace 返回空来源/未知 Token。

新增封闭规则：

- `required_context_sources`：必须存在指定来源；
- `excluded_context_sources`：不得存在指定来源；
- `max_context_tokens`：预算用量不得超过阈值。

CLI fixture 可以直接提供同样字段，保持无密钥 CI。规则仍不执行表达式、SQL 或用户代码。

### 5. 性能比较不使用单次端到端耗时归因

P4 主要比较同一候选集的上下文来源精度、选中数量和近似 Token；真实端到端耗时作为观察值，不因单次模型波动直接归因。后续若做延迟 Gate，需固定告警并多次运行取中位数。

## Risks / Trade-offs

- [旧 SOP 缺少路由 metadata] → 归入 `generic` 并受 Token 预算约束，不直接删除；教程要求重新 seed 以获得完整字段。
- [metadata 标注错误导致错误排除] → Snapshot 显示字段和原因，可人工复盘；上传 metadata 仍受 allowlist 约束。
- [近似 Token 与模型真实 Token 有偏差] → 命名和文档明确为 estimate，预算留安全余量。
- [截断破坏 SOP 语义] → 只允许首个来源截断并记录；优先依靠较小 chunk 和多来源排除，测试覆盖边界。
- [新规则对旧 Trace 缺少上下文字段] → 仅在 Dataset 显式声明 P4 规则时失败，旧 Dataset 行为不变。

## Migration Plan

1. 发布兼容的 Snapshot/合同字段和选择器。
2. 更新执行链 UI 与 Evaluation 规则目录。
3. 运行离线 fixture、单元/合同/前端测试。
4. 重启本地后端，重新运行 `PaymentGatewayTimeoutHigh`，用真实 Trace 建立 P4 Dataset。
5. 回滚只需恢复应用代码；旧 P4 step payload 会被旧前端忽略，不需数据库回滚。

## Open Questions

- P5 是否将同类预算策略扩展到 Chat 长对话 Memory；P4 只处理 AIOps Planner 的 SOP 上下文。
- 是否在更多真实告警积累后引入显式 SOP 适用范围管理；本版先使用现有 alert/service metadata。
