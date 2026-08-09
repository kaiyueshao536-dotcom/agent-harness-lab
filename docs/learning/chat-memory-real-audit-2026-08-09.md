# Chat 记忆真实审计（2026-08-09）

## 审计目标

在不修改业务代码的前提下，走真实 API、真实 Qwen 模型和当前 Chat 页面，验证长对话触发压缩后是否会出现：

1. 关键约束丢失；
2. 已废止的旧信息污染当前回答；
3. 压缩过程不可观测或不可恢复。

本次使用独立的本地审计账号和 4 个隔离会话。历史填充通过正式 `POST /chat/sessions/{id}/messages` 接口完成；第 31 轮通过页面发送，以真实触发 `every_30_turns` 自动压缩和后续 Agent 回答。未使用模拟 LLM。

## 当前实现事实

- `ChatMemoryService.prepare_message()` 在第 31 轮发送前同步执行压缩。
- 压缩把尚未压缩的全部消息拼成文本，再调用同一个 Chat 模型生成一段“不超过 1200 个汉字”的自然语言摘要。
- 1200 字只是提示词要求，没有结构化 schema、程序截断、关键信息校验或摘要质量 Gate。
- 压缩成功后，旧消息仍保存在 SQLite，但不会再发给 Agent；Agent 只接收摘要和新的用户消息。
- Chat Trace 在压缩成功后才创建。因此压缩耗时、重试和失败不属于现有 Trace。
- 会话 API 和页面只展示模式、占用率等状态，不展示摘要正文，用户无法检查模型实际保留了什么。

## 实验结果

### A：最高优先级约束保留

- Session：`chat_283eaac2e6d147b7bd0a955fa8c9c94c`
- 原始约束：`Python`、`琥珀-731`、`禁止数据库写操作`
- 压缩：成功，`compacted_message_count=60`，摘要 294 字
- 语义结果：三个值均保留，未复现约束丢失
- Trace：`trace_7de010a4416b4bc084b5414d7f1a3001`，只记录 `chat.agent` 的 3695 ms
- 额外异常：持久化回答被完整重复两次

实际持久化内容：

```text
LANGUAGE=Python
COLOR=琥珀-731
DB_WRITE=禁止任何数据库写操作LANGUAGE=Python
COLOR=琥珀-731
DB_WRITE=禁止任何数据库写操作
```

### B：旧值覆盖与污染

- Session：`chat_44e5dfa9691b487d852457856a729839`
- 旧值：`Java`、`蓝色-117`、`允许数据库写操作`
- 新值：`Python`、`绿色-908`、`禁止数据库写操作`
- 压缩：成功，`compacted_message_count=60`，摘要 357 字
- 语义结果：摘要明确标记旧值已废止，最终回答未引用旧值；本次没有复现旧信息污染
- Trace：`trace_f37b9da429be42a1a0fe8796d70e71dc`，只记录 `chat.agent` 的 3840 ms
- 额外异常：最终回答同样被完整重复两次

### C：有规律的容量边界

- Session：`chat_dfab016a60104479982602d65559e688`
- 输入：30 组 P0 约束，每组 7 个字段，并明确禁止推断
- 压缩：成功，`compacted_message_count=60`，摘要 921 字
- 抽查：C-17 最终值正确
- Trace：`trace_d88cde92363c4ab5ad2ad7d6244978c1`，只记录 `chat.agent` 的 9383 ms

但摘要没有逐条保存 C-17。模型自行归纳了编号映射规则，并声称“其余约束均严格按上述映射生成，已全量逐字记录”。这违反了用户明确写下的“不得从其他轮推断”约束。最终答案之所以正确，是因为测试数据恰好存在规律，而不是因为原始 C-17 被忠实保留。

这个结果证明当前摘要可能把“原始事实”替换成“模型推断”，并且系统没有来源标记和校验机制识别这种替换。

### D：不可推导的容量边界

- Session：`chat_9862e7ddc74143d38b7ed86ea006e6ce`
- 输入：30 组相互独立、不可推导的随机 P0 约束
- C-17 期望值：`svc-0a7f026b|own-1c0c417d|rb-a923c988|ff-f36d5bf6`
- 结果：自动压缩约 5—6 分钟后失败，没有生成摘要，也没有生成最终回答
- 数据库终态：`compacted_message_count=0`、`memory_summary=NULL`、原 60 条消息仍在，最终复核消息未持久化
- Trace：0 条。因为失败发生在 Trace 创建之前
- 页面表现：长时间只显示统一的“正在生成回答，请稍候”，终态只给通用失败反馈；没有“正在压缩”“模型重试次数”“压缩失败原因”或重试入口

该用例没有得到一个可供判分的错误答案，因为系统在语义丢失发生前就先发生了压缩可用性故障。这仍然是更直接的真实问题：越难压缩、越需要精确保留的上下文，越可能阻塞整个 Chat，而且现有 Trace 完全看不到这段耗时和失败。

## 已确认问题与优先级

### P0：压缩不在 Trace 内，失败形成观测黑洞

`prepare_message()` 在 `start_trace()` 之前执行。D 用例耗时数分钟且失败，但数据库中没有对应 Trace。成功用例的 Trace 也只显示最终 Agent 的 3.7—9.4 秒，不能代表用户实际等待时间。

### P0：自然语言摘要没有真实性边界

C 用例中，模型把不可推断的逐条事实改写为推导规则。当前系统没有区分“原文事实、用户约束、模型归纳和已废止信息”，也没有摘要前后校验或关键约束 Gate。

### P0：Chat 输出重复并被持久化

A、B、C 三个成功用例都出现完整答案重复。重复内容不是纯前端渲染问题，SQLite 中的 assistant message 已经重复。需要检查 LangChain 事件解析同时消费 `on_chat_model_stream` 与 `on_chain_stream(name=model)` 是否对同一内容累计两次。

### P1：压缩同步阻塞发送，且没有阶段状态与恢复入口

压缩与最终回答绑定在同一个 SSE 请求内。失败时最终用户消息也未持久化，用户难以确认是否需要重发，且没有幂等重试语义。

### P1：摘要不可检查、不可比较、不可评测

API 不返回 `memory_summary`，页面也不显示摘要版本、压缩覆盖范围和来源。现有 Evaluation Dataset 不能直接对“压缩前约束—摘要—压缩后回答”建立 Gate。

### P1：现有测试只验证流程，不验证记忆正确性

`tests/test_chat_memory.py` 的 fake model 总是返回固定非空摘要。测试只断言压缩次数、消息未删除和硬限制，没有覆盖：

- 关键约束逐字保留；
- 新值覆盖旧值；
- 摘要不得新增推断事实；
- 摘要超时与重试；
- 压缩 Trace/Span；
- 输出去重；
- 压缩失败后的消息一致性与用户重试。

现有 3 个测试均通过：

```text
uv run pytest tests/test_chat_memory.py -q --basetemp=var/pytest-memory-audit
... [100%]
```

这说明当前测试覆盖的是“压缩机制能运行”，不是“记忆内容可信且可恢复”。

## 结论边界

- 已真实复现：模型用推导规则替代原始约束、压缩长时间阻塞并失败、压缩失败无 Trace、成功回答重复持久化。
- 本次未复现：单组显著最高优先级约束丢失、明确覆盖后的旧值重新污染答案。
- 不能据此声称所有长对话都会丢约束；可以确认的是当前设计没有工程机制保证“不丢、不编、不污染”。

## 建议的下一步

先进入一个范围受控的 Chat 记忆闭环，而不是建设通用记忆平台：

1. 把 `chat.memory.compact` 纳入 Trace，并拆分 `summary.generate`、`summary.validate` Span；Trace 必须在压缩前创建。
2. 将摘要拆为结构化区域：`active_constraints`、`superseded_facts`、`decisions`、`open_tasks`、`evidence_refs`，每项保留来源 message id。
3. 对关键约束使用确定性抽取与覆盖规则；自然语言摘要只负责叙述，不作为唯一事实源。
4. 建立 Chat Memory Evaluation Dataset，至少复用 A—D 四类 Case，并对约束保留、旧值泄漏、摘要新增事实、耗时和失败恢复设置 Gate。
5. 修复流式事件去重，再评测记忆回答；否则重复输出会污染所有 Case 的字符串判分。
6. 压缩失败时保留可重试状态，显示阶段与错误分类，并避免让用户误以为最终消息已经发送成功。

## P5 修复落地状态

P5 已将上述建议落到一条受控的 Chat 记忆生命周期：

- 用户消息先落库，然后创建 Trace 并执行 `chat.memory.prepare`；压缩失败不再丢失本次消息。
- Memory Trace 包含 `prepare → compact → attempt / validate`，记录有界超时、尝试次数和错误分类。
- 快照改为 `activeConstraints` / `supersededFacts` / `decisions` / `preferences` / `openTasks` / `evidenceRefs`，条目的 value 必须在所属消息中逐字出现。
- LangChain adapter 不再同时消费 `on_chat_model_stream` 与重叠的 `on_chain_stream(name=model)`；持久化前另有精确双份防御。
- 桌面 Chat 页显示快照版本、压缩边界、当前/已废止条目、来源 message id 和失败重试入口。
- Memory Evaluation 新增约束保留、旧值泄漏、无来源事实、重复回答、压缩成功和耗时规则；A—D 无密钥 fixture 已通过 100% Gate。

这些结论已由迁移、service/API/Trace/Evaluation 测试、前端全量测试与 build 验证。真实浏览器又用 Qwen 跑通了 v0→v1 的来源保留和 v1→v2 的显式覆盖：`ap-shanghai` 成为唯一 active constraint，`ap-guangzhou` 进入 superseded facts，两个来源 message id 和覆盖关系都可在页面检查。A—D 的 100% Gate 仍明确属于确定性离线 fixture，不冒充四组真实模型长对话结果。
