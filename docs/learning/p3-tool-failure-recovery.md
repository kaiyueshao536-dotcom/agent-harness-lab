# P3 实操：外部工具失败与恢复

这份学习记录用于亲自跑通 P3，并准备面试追问。目标不是背代码，而是能用一次真实故障解释两种不同重试范围。

## 先回答四个问题

1. **Tool 与 Attempt 的区别**：Tool 是一次逻辑 SearchLog 调用；Attempt 是该调用连接 MCP Server 的一次尝试。
2. **MCP 重试与 Job 重试的区别**：前者只包围工具连接，后者从 Planner 到 Report 重新运行整个诊断。
3. **为什么保留旧 Trace**：失败 Trace 是根因和修复效果的对照证据，覆盖它会破坏审计与 Baseline。
4. **为什么不从失败节点继续**：当前尚未证明节点状态可重放，也没有为所有有副作用工具建立幂等语义。

## 实操步骤

### 1. 建立成功基线

1. 正常启动前端、FastAPI、CLS MCP Server。
2. 发起一次 AIOps 智能诊断并等待成功。
3. 在“执行追踪”记录 Trace ID，确认 `aiops.graph → SearchLog → SearchLog.attempt` 父子关系。
4. 记录 Tool、Attempt 的状态与耗时。

### 2. 注入真实且可恢复的故障

停止本机 CLS MCP Server，不修改凭据、不制造虚假 CLS 返回。再次发起相同诊断：

- Tool Audit 应显示 `SearchLog` 失败；
- Trace 中每次连接应各有一个失败 Attempt；
- 最终 Job 和 Trace 应失败；
- Attempt 属性只能看到序号、上限、连接名和错误类别。

### 3. 恢复并关联重试

重新启动同一个 MCP Server，在失败诊断中点击“重试本次诊断”：

- 新 Job ID 与旧 Job 不同；
- 新 Job 的 `retryOfJobId` 等于旧 Job ID；
- Diagnostic Task ID 保持不变；
- 新 Trace ID 与失败 Trace 不同；
- 旧失败 Job/Trace 仍可查询。

### 3.1 先确认失败态真的可操作

手工验收时不要只看“执行失败”四个字，还要确认：

- 已经生成降级报告时仍显示“重试本次诊断”；
- 报告明确标识为“失败后的降级报告”，不会被误认为成功产物；
- 公开报告不显示 MCP URL、Topic ID、密钥或原始异常正文；
- Trace 中 `SearchLog` 显示为 `↳`，它的 Attempt 显示为 `↳↳`；
- 每个 Attempt 显示 `第 N/M 次尝试`，但不展示任意 attributes。

如果 Alertmanager 可访问但返回 `[]`，正确状态是“当前告警源没有返回活跃告警”，不是“加载失败”。空结果和接口异常必须区分。

### 4. 用 Evaluation 证明修复

创建一个 AIOps Case，至少加入：

- `trace_succeeded`；
- `required_tools = SearchLog`；
- `min_references = 1`；
- 合理的 `max_duration_ms` 与 `max_tool_calls = 2`。本项目一次完整 AIOps 诊断包含 `knowledge_retrieval` 和 `SearchLog` 两个逻辑 Tool；MCP Attempt 不计入工具数量。

先绑定失败 Trace，记录 Gate 失败；再用相同 Dataset 绑定恢复 Trace，记录 Gate 结果。注意：Gate 只能检查 Dataset 已声明的规则，不能发现未定义的问题。

## 复盘表

| 项目 | 失败执行 | 恢复执行 |
| --- | --- | --- |
| Diagnostic Task ID |  |  |
| Job ID |  |  |
| retryOfJobId | 无 |  |
| Trace ID |  |  |
| Tool Span 数 |  |  |
| Attempt Span 数 |  |  |
| Gate | 失败 |  |
| 最重要的证据 |  |  |

## 本次真实验收样例

| 项目 | 失败执行 | 恢复执行 |
| --- | --- | --- |
| Diagnostic Task ID | `diagnostic_8d165d…` | 同一 Task |
| Job ID | `job_881d79…` | `job_575bc4…` |
| retryOfJobId | 无 | 指向 `job_881d79…` |
| Trace ID | `trace_ba4503…` | `trace_3bac50…` |
| Trace 状态 | failed | succeeded |
| Trace 耗时 | 69,436 ms | 85,571 ms |

这组数据说明重试没有覆盖旧失败记录，而是生成了新的恢复证据。完整复盘见 [`P3.1 版本记录`](../version-history/p3.1-manual-acceptance-gap-closure.md)。

## 常见追问

### 为什么不把每次 Attempt 记成 Tool？

因为评测的 `max_tool_calls` 和 Tool Audit 都表达逻辑业务调用。如果内部连接重试也算 Tool，会导致一次 SearchLog 被统计成两次，并让成本、审计和流程图都失真。

### 为什么 SearchLog 可以重试，创建工单不能直接照搬？

SearchLog 是只读查询，重复执行通常不会改变 CLS 数据。创建工单有副作用，如果请求成功但响应丢失，直接重试可能创建两张工单，需要先加入业务幂等键和结果查询。

### Trace succeeded 为什么不等于 Gate passed？

Trace succeeded 只说明程序走到完成；Gate 还会检查输出内容、引用、工具、耗时和数量是否满足 Dataset 规则。
