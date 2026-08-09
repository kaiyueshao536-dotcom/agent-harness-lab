## ADDED Requirements

### Requirement: Traced Chat memory lifecycle
每次 Chat 执行 SHALL 在记忆准备前创建 Trace，并用层级 Span 记录记忆准备、压缩、校验和 Agent 阶段；成功与失败都 MUST 终结 Trace。

#### Scenario: Chat triggers compression
- **WHEN** 已认证 user 的消息触发自动压缩
- **THEN** Trace MUST 包含 `chat.memory.prepare`、`chat.memory.compact`、`chat.memory.validate` 和 `chat.agent` 的父子关系与真实阶段耗时

#### Scenario: Compression fails before Agent
- **WHEN** 摘要模型超时、返回无效 schema 或未通过来源校验
- **THEN** Trace MUST 以失败状态结束并记录安全错误分类，且 MUST NOT 创建成功的 `chat.agent` Span

### Requirement: Safe memory trace attributes
记忆 Span SHALL 只记录模式、触发原因、消息计数、token、版本、attempt、状态和错误分类，MUST NOT 记录消息正文、事实值、摘要正文、凭据或模型原始异常。

#### Scenario: User message contains private data
- **WHEN** 包含私有内容的对话触发压缩
- **THEN** Trace attributes 和结构化日志 MUST 只保留安全元数据而不包含私有内容
