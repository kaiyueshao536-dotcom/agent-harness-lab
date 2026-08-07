# P1：统一 Agent Trace

## 版本信息

| 项目 | 内容 |
| --- | --- |
| 发布日期 | 2026-08-06 |
| 状态 | 已发布 |
| Commit | [`e3e7aac`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/e3e7aac9f009d37b4f5bc4f21007e05747f6c0a1) |
| Tag | [`p1-unified-agent-trace`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p1-unified-agent-trace) |
| OpenSpec | [`unify-agent-trace`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p1-unified-agent-trace/openspec/changes/unify-agent-trace) |
| 变更规模 | 41 个文件，2,787 行新增，15 行删除 |

## 背景与目标

P0 能证明项目可运行、可验证，但 Chat 和 AIOps 的执行信息分散在 SSE、日志、任务记录和工具审计中。遇到失败或性能问题时，无法使用统一标识还原一次 Agent 执行。

P1 的目标是建立统一 Trace/Span 数据模型，把一次执行从入口、阶段、工具调用到完成状态串联起来，并提供用户隔离的查询 API 与桌面时间线。

## 实现内容

### Trace 数据底座

- 新增 Agent Trace/Span SQLAlchemy 模型、Alembic 迁移和 owner/时间索引。
- 新增仓储协议与 SQLite 实现，覆盖创建、结束、列表、详情、顺序和用户隔离。
- 新增 `AgentTraceService`，统一 ID、状态、sequence、安全摘要和写入降级行为。

### Chat 与 AIOps 接入

- 流式聊天创建并终结 Trace，工具生命周期映射为 Span。
- 同一次 Chat SSE 的所有事件共享 `traceId`，工具事件携带 `spanId`。
- AIOps 将 Planner、Executor、Replanner、Report 和工具阶段映射为有序 Span。
- Trace 写入失败采取可观测降级，不让辅助观测能力无故破坏主执行链路。

### API、合同与工作台

- 新增 `GET /agent-traces` 和 `GET /agent-traces/{traceId}`。
- 更新共享 TypeScript 类型、OpenAPI 和 SSE Trace 上下文。
- 新增“执行追踪”桌面入口，支持类型/状态筛选、指标摘要和有序 Span 时间线。
- 不生成模拟 Trace；工作台只展示当前用户的真实执行数据。

### 安全边界

- Trace 和 Span 按 owner 查询，跨用户详情返回 404。
- 只保存安全摘要、状态、耗时和结构化标识。
- 不保存完整提示词、思维链、模型密钥或原始工具凭据。

## 关键设计决策

- **Chat 与 AIOps 使用同一模型**：避免为不同 Agent 路径维护两套不可比较的观测体系。
- **Span 使用显式 sequence**：时间戳相同或异步事件交错时仍能稳定还原执行顺序。
- **Trace 是观测能力，不是主链路单点**：持久化异常被记录并降级，业务失败状态仍尽可能完成收口。
- **先做安全结构化摘要**：可追溯不等于保存所有上下文，优先控制敏感数据暴露面。

## 关键文件

- [`apps/backend/src/super_ai/tracing.py`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p1-unified-agent-trace/apps/backend/src/super_ai/tracing.py)
- [`apps/backend/src/super_ai/memory/trace_sqlite.py`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p1-unified-agent-trace/apps/backend/src/super_ai/memory/trace_sqlite.py)
- [`apps/frontend/src/views/TraceView.vue`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p1-unified-agent-trace/apps/frontend/src/views/TraceView.vue)
- [`apps/frontend/src/components/AgentTraceTimeline.vue`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p1-unified-agent-trace/apps/frontend/src/components/AgentTraceTimeline.vue)
- [`packages/api-contracts/src/traces.ts`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p1-unified-agent-trace/packages/api-contracts/src/traces.ts)
- [`openspec/changes/unify-agent-trace/`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p1-unified-agent-trace/openspec/changes/unify-agent-trace)

## 验证结果

版本验证覆盖：

- Trace/Span 迁移、仓储、权限隔离和稳定排序。
- Chat、AIOps 成功/失败、工具 Span 复用和写入降级。
- API 筛选、详情、404 权限边界、OpenAPI 与 SSE 合同。
- 前端路由、客户端、状态、空状态、筛选和时间线渲染。
- OpenSpec、Ruff、Pyright、Pytest、合同检查、前端类型检查、测试与构建。
- 敏感字段静态复核。

当时没有保留可靠的完整测试通过数量，因此只记录可由代码和 tasks 核验的覆盖范围。

## 已知限制

- Trace 能还原执行，但还不能自动判断结果质量是否退化。
- 没有版本化数据集、质量门禁和历史基线比较。
- 安全摘要适合排障与评测绑定，不等同于完整业务正文归档。

这些限制直接形成 P2 自动评测 Harness 的输入。

## 复盘结论

P1 把 Agent 从“能运行”提升为“执行过程可追踪”。它也是后续 Harness 的关键前置条件：没有稳定、统一、用户隔离的 Trace，自动评测就只能依赖脆弱日志或人工复制结果。

## 查看与回退

```powershell
git fetch --tags origin
git switch --detach p1-unified-agent-trace
```

如需从 P1 开始实验：

```powershell
git switch -c codex/review-p1 p1-unified-agent-trace
```
