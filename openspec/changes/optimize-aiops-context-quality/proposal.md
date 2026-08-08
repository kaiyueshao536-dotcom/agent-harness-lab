## Why

P3.3 已阻止历史诊断案例进入 Planner，但真实支付告警的 SOP-only Top 3 仍包含与当前服务无关的搜索 ES 超时 SOP。仅按知识角色和语义分数召回会浪费上下文并增加错误关联风险，当前 Snapshot 也无法回答“为什么排除这条来源、上下文用了多少预算”。

## What Changes

- 在 SOP-only 结果上增加告警名称与服务元数据的确定性相关性分层，明确选中、排除和退化原因。
- 为进入 Planner 的 SOP 正文设置固定 Token 预算；按优先级选择并在必要时安全截断，不把无限 Top K 直接送入模型。
- 扩展 Context Snapshot，记录候选来源、选择决策、估算 Token、预算用量和策略版本，不保存完整正文或 Prompt。
- 在执行链展示上下文预算、命中与排除来源，帮助复盘“检索问题还是上下文选择问题”。
- 扩展 Evaluation 确定性规则，支持必需上下文来源、禁止上下文来源和最大上下文 Token；提供 P4 无密钥 fixture。
- 用真实 `PaymentGatewayTimeoutHigh` 场景验证支付 SOP 保留、搜索 ES SOP 排除，并比较 P3.3 Top 3 与 P4 策略的来源精度和上下文体量。

## Capabilities

### New Capabilities

- `aiops-context-budgeting`: AIOps Planner 对 SOP 候选执行可解释的元数据相关性选择、Token 预算和安全退化。
- `aiops-context-quality-observability`: Context Snapshot 和桌面执行链展示候选、选择/排除原因及预算使用。
- `agent-context-quality-gates`: Trace-backed Evaluation 对 AIOps 上下文来源和 Token 用量执行确定性质量门禁。

### Modified Capabilities

无。

## Impact

- 影响 AIOps Planner、Context Snapshot 合同与执行链组件。
- 影响 Evaluation observation、规则目录、CLI fixture、API Trace 解析和前端规则 Builder。
- 不新增数据库表，不拆 Milvus Collection，不修改 MCP/CLS 协议，不引入新外部依赖。
- 离线测试与 Gate 不调用模型、Milvus、MCP 或 CLS；真实手工验收仍会产生一次现有诊断链路用量。
