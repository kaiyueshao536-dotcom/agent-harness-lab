## Context

当前 `ChatMemoryService` 在 Agent Trace 创建之前同步调用 Chat 模型，把压缩边界之前的全部消息改写为一段自由文本。旧消息仍在 SQLite，但后续 Agent 只看到摘要，因此摘要一旦遗漏、混淆或新增事实，运行时没有第二条事实链可校验。真实审计还确认了三个交叉问题：复杂摘要调用可阻塞数分钟且没有 Span，压缩失败时本轮消息没有可靠的恢复身份，以及 LangChain 的重叠流事件会把同一答案累计两次。

P5 涉及 Chat service、SQLite、Trace、SSE、Evaluation 和 Vue 桌面页面。实现必须继续按 user 隔离，不记录敏感正文到 Trace，不引入新的外部数据库或分布式任务系统。

## Goals / Non-Goals

**Goals:**

- 让每次 Chat 请求从记忆准备开始就拥有统一 Trace，并可区分压缩、校验和 Agent 阶段。
- 让当前有效约束与已废止事实拥有来源 message id，阻止无来源推断进入事实记忆。
- 让压缩超时或校验失败保持原始消息与旧快照不变，并允许使用同一 user message 重试。
- 让 SSE、数据库和页面只出现一次最终答案。
- 用确定性 Dataset 和 Gate 证明约束保留、旧值隔离、不可推导值、失败恢复和输出唯一性。

**Non-Goals:**

- 不构建跨 Chat、AIOps 和知识库共享的长期用户画像。
- 不引入 Kafka、Celery、Redis、外部记忆服务或通用分布式恢复平台。
- 不尝试从任意自然语言中完美抽取所有事实；P5 只保证被模型标记为结构化记忆的条目必须可追溯、可校验。
- 不保存或展示模型隐藏推理。

## Decisions

### Decision 1：在 `chat_sessions` 上持久化版本化 JSON 快照

新增 `memory_snapshot`、`memory_version`、`memory_status`、`memory_error_category` 和 `last_memory_attempt_at`。快照包含：

- `activeConstraints[]`：`key`、`value`、`sourceMessageId`；
- `supersededFacts[]`：旧值、来源和覆盖它的新消息；
- `decisions[]`、`preferences[]`、`openTasks[]`、`evidenceRefs[]`；
- `narrativeSummary` 与压缩边界元数据。

选择 JSON 而不是立即拆成多张关系表，是因为这些字段只随会话压缩事务更新，当前查询模式也是整份读取。schema 由 Pydantic v2 严格校验；以后若需要跨会话检索再迁移到规范化表。

替代方案是继续只存自然语言摘要；它无法表达来源和覆盖关系，已被审计证明不可靠。另一方案是为每类记忆建表，当前规模下会放大迁移和 repository 复杂度。

### Decision 2：模型提出候选快照，程序决定是否接受

摘要模型必须返回 JSON。程序仅接受满足以下条件的候选：

- 所有 message id 属于本 user、本 session 且位于本次输入或旧快照来源中；
- `value` 能在对应来源消息正文中逐字找到；
- `supersededByMessageId` 指向较新的来源；
- 同一 `key` 最多有一个 active value；
- narrative summary 只由已经验证的结构化条目和安全截断生成，不直接作为事实源。

校验失败不得推进压缩边界。旧快照和完整消息历史保持不变。这样允许模型帮助抽取，但不允许模型推断冒充事实。

### Decision 3：显式覆盖采用可审计的候选关系

模型可通过 `supersedesSourceMessageIds` 提出覆盖关系，程序验证新来源时间晚于旧来源，并将旧条目移动到 `supersededFacts`。Agent system prompt 只注入 `activeConstraints`、当前 decisions/preferences/open tasks 和 narrative summary；已废止值仅在用户显式询问历史时可通过完整会话历史/API 查看，不默认注入当前上下文。

### Decision 4：Trace 在记忆准备前创建

流式请求先创建 `chat` Trace，再开始 `chat.memory.prepare` Span；发生压缩时增加 `chat.memory.compact` 和 `chat.memory.validate` 子 Span，最后才创建 `chat.agent`。Span attributes 只包含计数、版本、模式、原因、token、attempt 和 error category，不包含消息正文或摘要正文。

手动压缩 API 也创建独立 `chat_memory` execution trace。成功和失败都必须终结 Trace。

### Decision 5：用户消息先持久化，再对旧历史压缩

服务先保存带有稳定 message id 的 user message，然后仅压缩它之前的未压缩历史，把该 message 作为压缩后的第一条新消息交给 Agent。压缩失败时该消息保留，并在 metadata 中记录 `memoryPreparationStatus=failed` 和 trace id。新增 retry endpoint 使用原 message id 重跑，不再次插入 user message。

这比“失败时不保存”更符合用户看到的发送动作，也为幂等重试提供稳定身份。

### Decision 6：按事件身份和累计内容双重去重

LangChain adapter 优先消费 `on_chat_model_stream`；当同一 run 已出现模型流事件时，忽略对应 `on_chain_stream(name=model)` 兼容事件。Streaming service 仍对连续累计文本做防重保护，避免 provider adapter 变化再次污染持久化内容。

### Decision 7：复用现有 Evaluation Harness，增加 memory case 规则

Dataset case 绑定 Chat session/trace 与预期 active/superseded 值。确定性规则读取持久化 memory snapshot 和 assistant message，不让 LLM 自评。聚合指标至少包含 constraint retention、superseded leakage、unsupported fact、duplicate output、compression success 和 duration。Gate 使用现有 baseline/run 模型，不另建第二套评测平台。

## Risks / Trade-offs

- [模型不能稳定返回合法 JSON] → 使用 Pydantic 严格解析、短超时、有限重试；失败保持旧快照并提供重试。
- [逐字来源校验会拒绝合理改写] → P5 优先真实性；`value` 必须来自原文，叙述性改写只放在非事实摘要中。
- [先持久化 user message 改变现有失败语义] → metadata 明确 failed/pending 状态，retry endpoint 复用该消息，并用 API 测试保证不重复。
- [JSON 快照后续查询不便] → 当前只按 session 整体读取；保留版本字段和迁移路径。
- [Trace attributes 泄露上下文] → 仅记录计数、标识符和分类，禁止正文、值和摘要。
- [评测规则变多导致旧 Dataset 不兼容] → 新规则为可选类型，旧 Dataset 和 run 保持可读。

## Migration Plan

1. 新增 nullable JSON/status/version 列；现有 `memory_summary` 保留作兼容读取。
2. 首次读取旧会话时生成只含 `narrativeSummary` 的 legacy 快照，不伪造来源条目。
3. 新压缩成功后同时更新结构化快照与兼容摘要字段。
4. 前端对缺少快照的旧会话显示“旧版摘要，来源不可追溯”。
5. 若需回滚代码，新列不会影响旧版本；旧 `memory_summary` 仍可继续使用。

## Open Questions

- P5 完成真实验收后，再决定是否把 memory Dataset 作为默认仓库示例数据提交；实现阶段先提供可重复 fixture 和教程。
