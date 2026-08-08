## Why

P3 的真实浏览器验收发现，底层恢复数据虽然已经正确持久化，但界面无法展示 Span 父子关系与 Attempt 次数；失败任务生成降级报告时还会隐藏重试入口。与此同时，报告会泄露内部连接信息，未启用的告警源占位配置也会让健康的本地 Alertmanager 整体不可用，因此需要用一次小范围 P3.1 修复完成真实交互闭环。

## What Changes

- Trace 时间线根据 `parentSpanId` 展示父子缩进与连接关系，并为 Attempt 展示“第 N/M 次尝试”、安全错误类别等白名单属性。
- 失败诊断即使已经生成降级报告，也始终展示明确的重试入口，并用“失败后的降级报告”而非成功语义标记产物。
- 面向用户的 AIOps 报告不再包含 MCP URL、CLS Topic ID 等内部连接或资源标识；完整诊断凭证仍保留在受权限控制的 Tool Audit。
- 告警源配置增加显式 `enabled` 状态；未启用的占位源不参与校验和请求，至少一个启用且有效的告警源即可正常返回结果。
- 增加真实组合场景的回归测试，并记录 P3.1 的问题、根因、修复和复测证据。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `request-observability`: Agent Trace 必须在 UI 中展示可理解的父子层级与安全 Attempt 元数据。
- `aiops-diagnosis-ui`: 失败任务即使存在降级报告也必须提供重试入口，并正确区分失败产物与成功报告。
- `real-mcp-tools`: 面向用户的失败摘要必须隐藏 MCP 连接地址和 CLS 内部资源标识。
- `active-alert-subscription-entry`: 未启用的告警源不得阻断已启用告警源，空告警集合必须作为成功结果展示。
- `shared-user-project-configuration`: 告警源必须支持显式启停，并只校验启用的配置项。

## Impact

- 前端：Trace 时间线、AIOps 报告面板及对应组件测试。
- 后端：告警源配置构建、AIOps 失败摘要/报告脱敏及对应服务/API 测试。
- 配置：`config/project*.json` 的告警源增加 `enabled` 字段，本地占位 Prometheus 默认关闭。
- 文档：README、CHANGELOG、P3.1 版本复盘与学习记录。
- 不修改数据库结构，不引入新的基础设施或第三方可视化框架。
