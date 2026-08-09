# P5：Chat 记忆与上下文生命周期闭环

## 问题来源

P5 不是为了增加一个抽象的“记忆功能”，而是修复 2026-08-09 真实长对话审计里复现的四个问题：

1. 压缩在 Trace 创建前同步阻塞，5—6 分钟失败后没有 Trace。
2. 自然语言摘要把原始事实改写为模型推导，没有来源校验。
3. LangChain 重叠流事件使完整回答显示两遍，且重复内容被持久化。
4. 失败时最终用户消息也未落库，页面只有通用错误，无法判断是否要重发。

## 核心改动

### 1. 可追溯的结构化快照

Chat session 增加 `memory_snapshot`、`memory_version`、`memory_status`、`memory_error_category` 和 `last_memory_attempt_at`。快照的事实条目保存 `sourceMessageId`，已覆盖的条目额外保存 `supersededByMessageId`。

模型只提出 JSON 候选，程序确定性校验：

- value 必须是来源消息中连续出现的原文；
- 来源必须属于当前 user 和 session；
- 同一 active key 只能有一个值；
- supersession 的替换消息必须比旧消息新。

### 2. 失败可观测且可恢复

新链路为：

```text
用户消息落库
  → 创建 Chat Trace
  → chat.memory.prepare
      → chat.memory.compact
          → chat.memory.compact.attempt
          → chat.memory.validate
  → chat.agent
  → assistant message 落库
```

压缩单次默认上限 45 秒，最多 2 次尝试。失败时不推进 `compacted_message_count`，不覆盖上一版快照。用户消息保留 `memoryPreparationStatus=failed`、错误分类、Trace ID 和尝试次数。重试 API 复用原 message id，不新增重复 user message。

### 3. 流式正确性

LangChain adapter 以 `on_chat_model_stream` 作为 ChatOpenAI 的内容增量来源，忽略重叠的 `on_chain_stream(name=model)`。持久化前对“完整文本恰好重复两次”做第二层防御。

### 4. 可检查的桌面页面

Chat 页新增 Memory Inspector，展示：

- 快照版本、最近状态、压缩边界；
- active constraints 和 superseded facts；
- 来源 message id 及覆盖关系；
- 当前 SSE memory stage；
- 失败消息的重试入口。

### 5. Memory Evaluation Gate

现有 Evaluation Harness 新增六类确定性规则：

- `memory_contains_active`
- `memory_excludes_active`
- `memory_no_ungrounded`
- `memory_compaction_succeeded`
- `no_exact_duplicate`
- `max_memory_duration_ms`

`evals/fixtures/p5-chat-memory-lifecycle-pass.json` 覆盖 A—D 四类审计场景，无需模型或云凭据即可重放 Gate。

## 验证记录

- P5 后端定向测试：32 项通过。
- 后端全量 pytest：通过（1 项按环境条件跳过）。
- Pyright：0 errors。
- Ruff：全量通过。
- 前端 Vitest：27 个测试文件、101 项测试通过。
- API contracts typecheck 与前端 Vite production build：通过。
- P5 离线 fixture：Gate passed，pass rate 100%，average score 100%。
- OpenSpec：53 项 change/spec 验证通过。

真实桌面浏览器使用本地测试账号和真实 Qwen 完成两轮验收：

1. 首轮从 v0 压缩到 v1，边界为 2 条，提取 `部署区域=ap-guangzhou` 并保留来源 message id；Trace `trace_d0a0d8e057384a7d8b9d147a51de95c1` 成功，Span 为 `compact → attempt → validate`。
2. 显式把部署区域覆盖为 `ap-shanghai` 后，从 v1 压缩到 v2，边界为 4 条；新值成为唯一 active constraint，旧值进入 superseded facts，并记录旧、新 message id 的覆盖关系。Trace `trace_74da4356f7e64ef096e069ae46714b6e` 成功，失败 Span 为 0。
3. 验收过程中真实遇到 Qwen 把 `evidenceRefs` 输出为字符串数组的问题。系统连续两次拒绝无效候选且未推进版本或边界；随后增加安全归一化，归一化后的 message id 仍需通过 owner/session 范围校验。Trace 仅保存固定错误码，不保存模型原文。

## 面试可讲的闭环

我先通过真实长对话复现了“摘要推断污染、压缩观测黑洞、流式重复和失败丢消息”。然后把记忆改为“模型提候选，程序验来源”，把 Trace 移到压缩前，用有界重试和同 message id 恢复保证一致性，最后用确定性 Dataset/Gate 防回归。这个范围只解决已复现的 Chat 问题，没有包装成分布式记忆平台。

## 已知边界

- 压缩仍在 Web 请求进程内执行，超时和重试是有界的，但不是持久队列。
- 快照当前保存最新版本和版本号，完整的每版历史依赖 Git 版本与原始 Chat message，尚未建立独立 snapshot history 表。
- 结构化抽取仍使用 LLM 提候选；程序能拒绝无来源值，但不能保证模型一定选中所有重要条目。这由 Memory Dataset/Gate 持续补上。
