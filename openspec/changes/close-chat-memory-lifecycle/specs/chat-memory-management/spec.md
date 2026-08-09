## ADDED Requirements

### Requirement: Versioned structured memory snapshot
系统 SHALL 为每个 Chat session 持久化 owner-scoped、版本化的结构化记忆快照，区分当前约束、已废止事实、决策、偏好、未完成事项、证据引用和叙述摘要；事实条目 MUST 包含来源 message id。

#### Scenario: Compression creates a structured snapshot
- **WHEN** 一个会话成功压缩可压缩历史
- **THEN** 后端 MUST 原子更新快照、版本、兼容摘要、压缩边界和成功状态

#### Scenario: Existing legacy summary is read
- **WHEN** 旧会话只有 `memory_summary` 且没有结构化快照
- **THEN** 后端 MUST 将其标记为来源不可追溯的 legacy 摘要，且 MUST NOT 伪造结构化事实来源

### Requirement: Source-grounded memory validation
系统 SHALL 在推进压缩边界前校验候选记忆，事实值 MUST 在 owner-scoped 来源消息中逐字存在，来源与覆盖关系 MUST 属于当前 session 且时间顺序有效。

#### Scenario: Candidate contains an unsupported inferred fact
- **WHEN** 摘要模型返回无法在声明来源消息中逐字找到的事实值
- **THEN** 系统 MUST 拒绝候选、保留旧快照与压缩边界并记录安全错误分类

#### Scenario: Candidate cites another user's message
- **WHEN** 候选快照引用不属于当前 owner 或 session 的 message id
- **THEN** 系统 MUST 拒绝候选且 MUST NOT 暴露该消息是否存在

### Requirement: Deterministic supersession lifecycle
系统 SHALL 验证新事实对旧事实的显式覆盖关系，同一 key MUST 最多保留一个当前有效值，被覆盖值 MUST 进入已废止区且不得默认注入当前 Agent 上下文。

#### Scenario: User explicitly replaces an old value
- **WHEN** 较新的消息明确覆盖相同 key 的旧值且候选关系通过来源校验
- **THEN** 新值 MUST 成为 active constraint，旧值 MUST 记录来源和覆盖消息并进入 superseded facts

#### Scenario: Agent continues after supersession
- **WHEN** 系统为后续 Agent 调用装配记忆上下文
- **THEN** 默认上下文 MUST 包含当前值且 MUST NOT 把已废止值描述为当前事实

### Requirement: Recoverable compression attempt
系统 SHALL 使用独立超时和有限重试执行压缩；失败 MUST 保留完整原始历史、旧快照和旧压缩边界，并保存可重试状态与安全错误分类。

#### Scenario: Summary model times out
- **WHEN** 摘要生成达到配置的压缩超时和最大尝试次数
- **THEN** session MUST 标记压缩失败，原始消息和旧快照 MUST 保持不变，客户端 MUST 获得可重试结果

#### Scenario: Failed compression is retried
- **WHEN** user 对失败的稳定 message id 请求重试且随后压缩成功
- **THEN** 系统 MUST 复用原 user message、生成一个新 Trace，并且 MUST NOT 插入重复 user message

### Requirement: Inspectable memory lifecycle
会话 API SHALL 返回安全的记忆版本、状态、覆盖范围、最近尝试时间、错误分类、当前约束、已废止事实及来源 message id，桌面 Chat 页面 MUST 支持检查这些信息。

#### Scenario: User inspects a compressed session
- **WHEN** owner 读取已压缩会话
- **THEN** 响应和页面 MUST 显示当前记忆版本、最近状态、压缩边界和来源可追溯的 active/superseded 条目

#### Scenario: User inspects a failed attempt
- **WHEN** 最近一次记忆准备失败
- **THEN** 页面 MUST 显示失败阶段、安全错误分类和重试动作，而不是继续显示统一生成状态

## MODIFIED Requirements

### Requirement: Compression preserves full history
记忆压缩 SHALL 只更新经过校验的结构化快照、兼容摘要和压缩边界，MUST NOT 删除或改写 SQLite 中的原始聊天消息；失败时 MUST NOT 推进压缩边界或替换上一版有效快照。

#### Scenario: User reads compressed session
- **WHEN** user 读取已经执行过压缩的会话历史
- **THEN** API MUST 返回压缩前后所有原始消息，模型请求 MUST 只包含经过校验的当前记忆和压缩边界后的消息

#### Scenario: Compression fails validation
- **WHEN** 候选快照未通过 schema、来源或覆盖校验
- **THEN** 原始历史、上一版快照和压缩边界 MUST 保持不变
