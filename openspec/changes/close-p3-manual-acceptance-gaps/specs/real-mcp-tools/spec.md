## ADDED Requirements

### Requirement: 面向用户的 MCP 失败内容最小披露
系统 SHALL 在 AIOps 降级报告和其他面向用户的失败摘要中只公开工具名、安全错误类别与恢复建议，并 MUST NOT 公开 MCP URL、CLS Topic ID 或凭据。

#### Scenario: MCP 调用失败并生成降级报告
- **WHEN** SearchLog 因 MCP Server 不可用而失败并进入 Replanner/Report
- **THEN** 报告 MUST 说明 SearchLog 外部工具不可用，MUST NOT 包含 MCP URL 或 CLS Topic ID

#### Scenario: 运维人员查看 Tool Audit
- **WHEN** 有权限的 owner 查看失败 Tool Audit
- **THEN** 审计记录 MAY 保留完成排障所需的受控调用信息，且 MUST 继续遵守 owner 隔离
