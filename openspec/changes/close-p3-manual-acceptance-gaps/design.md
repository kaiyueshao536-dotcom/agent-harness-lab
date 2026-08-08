## Context

P3 已经把 `parentSpanId`、`attemptNumber`、`maxAttempts` 和安全错误类别写入 Trace，但时间线仍按 sequence 展平。真实 MCP 失败还会经过 Replanner 生成一份证据不足的降级报告，现有 `v-if="report"` 会使失败分支和重试按钮永远不可达。告警订阅的聚合器本可容忍运行时单源失败，但 Provider 构建阶段会校验未配置的占位源，导致健康 Alertmanager 也被阻断。

## Goals / Non-Goals

**Goals:**

- 让研发展示能够直接读出 Trace 的父子关系和每次 Attempt。
- 保持“失败任务 + 降级报告 + 可重试”三种状态可以同时表达。
- 在进入面向用户报告前移除内部连接地址和 CLS 资源标识。
- 让显式关闭的告警源不影响其他启用源。
- 用自动化和真实浏览器场景复测五个缺口。

**Non-Goals:**

- 不实现复杂拓扑图、Span 折叠虚拟化或分布式链路查询。
- 不改变 Tool Audit 的完整审计数据和权限边界。
- 不为告警源增加动态管理后台。
- 不扩展 MCP/Job 的重试策略。

## Decisions

1. **保持 sequence 顺序，用 `parentSpanId` 计算展示深度。** 前端构建 `id → span` 索引并沿父链计算深度，使用缩进和连接线表达层级；不会重排执行顺序，也不会引入图可视化依赖。循环或缺失父节点回退到根层级。
2. **Attempt 只展示白名单属性。** 时间线仅显示 `attemptNumber`、`maxAttempts`、`errorCategory` 和 `attemptCount`，不提供任意 attributes JSON 展开，避免重新暴露参数、URL 或凭据。
3. **重试动作与报告正文解耦。** `taskFailed && canRetry` 时始终渲染重试按钮；存在报告时显示“失败后的降级报告”，保留报告正文但不使用成功状态语义。
4. **在报告输入边界进行脱敏。** Tool Audit 保留真实受控凭证；提供给 Replanner/Report 和面向用户摘要的错误文本统一替换 URL、Topic ID 等内部标识，只保留安全错误类别和可操作建议。
5. **告警源使用显式 `enabled`，并保持兼容。** 缺少 `enabled` 的既有配置按启用处理；`enabled=false` 的条目在必填字段校验前跳过。模板中的外部占位源关闭，本地 Alertmanager 启用。

## Risks / Trade-offs

- [深度缩进在异常父链下可能误导] → 对循环、孤儿父节点做保护并用单元测试覆盖。
- [过度脱敏降低排障信息] → Tool Audit 继续保存原始受控信息，用户报告保留工具名和安全错误类别。
- [旧配置没有 `enabled`] → 默认视为启用，避免已有真实告警源突然失效。
- [失败报告仍可能被误认为成功] → 状态徽标和重试入口都以任务状态优先，明确标注为降级报告。
