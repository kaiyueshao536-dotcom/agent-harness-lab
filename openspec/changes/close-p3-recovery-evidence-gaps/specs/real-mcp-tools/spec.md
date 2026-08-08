## ADDED Requirements

### Requirement: 面向用户的资源标识占位符格式稳定
系统 SHALL 将 MCP URL、CLS Topic ID 和凭据替换为稳定的安全占位符，并 MUST NOT 因原始括号或标点残留产生重复右括号、部分标识泄漏或破损文本。

#### Scenario: Topic ID 位于括号内
- **WHEN** 报告包含形如 `TopicId: <真实标识>]` 或 `TopicId: <真实标识>】` 的文本
- **THEN** 用户可见文本 MUST 只包含一次 `[内部资源标识已隐藏]`，MUST NOT 包含真实标识或 `]]`/`]】`

#### Scenario: MCP URL 和凭据同时出现
- **WHEN** 失败详情包含 MCP URL、Topic ID 和云凭据模式
- **THEN** 用户可见报告、SSE 和证据链响应 MUST 使用安全占位符，MUST NOT 返回任一原始值
