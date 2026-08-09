## Why

真实长对话审计表明，当前 Chat 记忆压缩会在 Trace 创建之前同步调用模型：摘要可能用模型推断替代原始约束，复杂上下文可能阻塞数分钟并失败，且成功回答存在重复持久化。现有测试只验证“发生过压缩”，无法证明关键约束未丢失、旧值未污染或失败后能够恢复，因此需要在进入更多 Agent 能力前先闭合 Chat 记忆生命周期。

## What Changes

- 修复 Chat 流式事件重复消费，保证 SSE、页面和 SQLite 中的最终回答只出现一次。
- 将记忆准备与压缩置于 Chat Trace 内，记录压缩原因、边界、token、尝试、耗时、状态和安全错误分类。
- 将单段自然语言摘要升级为带来源消息 ID 的结构化记忆，区分当前约束、已废止事实、决策、偏好、未完成事项和证据引用。
- 为显式覆盖建立确定性规则，使新值进入当前约束、旧值进入已废止区，并防止旧值默认进入 Agent 当前事实上下文。
- 在推进压缩边界前执行摘要 schema、来源、约束保留和新增事实校验；失败时保留原始历史并提供明确、可重试的状态。
- 增加独立压缩超时和有限重试，向 SSE/页面暴露“准备、压缩、校验、回答”阶段，而不是长期停留在统一生成状态。
- 增加 Chat Memory Evaluation Dataset 与 Gate，覆盖关键约束保留、旧值泄漏、不可推导值、超时恢复和重复输出。
- 在桌面 Chat 页面展示最近压缩状态、覆盖范围、当前约束、已废止信息和来源，不建设跨业务的通用记忆平台。

## Capabilities

### New Capabilities

- `chat-memory-quality-gate`: 定义 Chat 记忆回归 Dataset、确定性评分、聚合指标和发布 Gate。

### Modified Capabilities

- `chat-memory-management`: 将自然语言摘要压缩升级为可追溯、可校验、可恢复的结构化会话记忆生命周期。
- `stream-rag-chat`: 去除重复内容事件，增加记忆阶段 SSE，并保证压缩失败时的消息一致性与安全重试。
- `request-observability`: 将 Chat 记忆准备、压缩与校验纳入安全的 Trace/Span 和生命周期日志。

## Impact

- 后端：`super_ai.chat.memory`、`super_ai.chat.streaming`、Trace 服务、SQLite repository 与迁移、Evaluation service/API。
- 前端：Chat store/client、SSE contract、记忆设置与检查区域、失败重试交互。
- 合同：会话 memory payload、Chat SSE 事件、Trace Span attributes、Evaluation rule/metric。
- 测试：后端服务/API/SQLite/Trace/Evaluation 测试与前端桌面交互测试。
- 文档：README、学习复盘、P5 版本历史与面试讲解材料。
- 不引入新的分布式队列、外部记忆数据库或通用工作流平台。
