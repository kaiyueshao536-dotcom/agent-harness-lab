## ADDED Requirements

### Requirement: Unique final answer stream
Chat 流 SHALL 对重叠的模型事件进行去重，使每段最终答案内容在 SSE、持久化 assistant message 和页面中只出现一次。

#### Scenario: Provider emits model and chain stream events for the same content
- **WHEN** LangChain 为同一模型 run 同时发出 `on_chat_model_stream` 和兼容的 `on_chain_stream`
- **THEN** adapter MUST 只生成一组最终内容 delta，持久化正文 MUST 与模型原始答案一致且不重复

### Requirement: Memory lifecycle stream stages
Chat SSE SHALL 在适用时发出 `memory.stage` 事件，安全表达 `preparing`、`compacting`、`validating`、`completed` 或 `failed` 阶段及 Trace/Span 标识。

#### Scenario: Automatic compression runs before the Agent
- **WHEN** 当前消息触发自动压缩
- **THEN** 客户端 MUST 能区分记忆压缩、记忆校验和 Agent 回答阶段，事件 MUST NOT 包含消息或摘要正文

#### Scenario: Compression fails
- **WHEN** 记忆准备在 Agent 启动前失败
- **THEN** 流 MUST 发送统一错误与可重试 message id，且 MUST NOT 发送伪成功 complete 事件

### Requirement: Idempotent failed-message retry
后端 SHALL 为记忆准备失败后已持久化的 user message 提供 owner-scoped 重试操作，重试 MUST 复用原消息并创建新的执行 Trace。

#### Scenario: Owner retries a failed message
- **WHEN** owner 对当前 session 中标记为记忆准备失败的 user message 执行重试
- **THEN** 后端 MUST 不新增 user message，并重新运行记忆准备和 Agent

#### Scenario: Another user retries the message
- **WHEN** 非 owner 对该 message id 请求重试
- **THEN** 后端 MUST 返回统一授权错误且 MUST NOT 启动 Trace 或 Agent

## MODIFIED Requirements

### Requirement: Streaming chat persistence
后端 SHALL 通过 SQLite repository 保留聊天过程，并为 user message 保存稳定执行状态以支持记忆准备失败后的幂等重试。

#### Scenario: User message is persisted before memory preparation
- **WHEN** 接受流式聊天请求
- **THEN** 后端 MUST 在记忆准备和 Agent 执行之前保存 user message，并仅压缩该消息之前的历史

#### Scenario: Assistant message is persisted after final answer
- **WHEN** Agent 完成唯一的最终答案
- **THEN** 后端 MUST 持久化一条包含非重复最终内容、详细引用元数据、工具调用 ID 和 Trace ID 的助手消息

#### Scenario: Failed memory preparation preserves retry identity
- **WHEN** 记忆准备在 Agent 执行前失败
- **THEN** 后端 MUST 保留一条标记失败状态和 Trace ID 的 user message，MUST NOT 保留 assistant message

#### Scenario: Failed Agent stream avoids partial assistant persistence
- **WHEN** Agent 流在最终助手回答完成前失败
- **THEN** 后端 MUST NOT 保留部分 assistant message，并 MUST 在既有 user message 上记录失败状态
