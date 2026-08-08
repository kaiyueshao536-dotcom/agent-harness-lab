# P3：Trace 驱动的外部工具失败恢复闭环

## 版本信息

| 项目 | 内容 |
| --- | --- |
| 发布日期 | 2026-08-08 |
| 状态 | 已发布 |
| Commit | 以发布 Tag 的不可变指向为准 |
| Tag | [`p3-trace-driven-tool-failure-recovery`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p3-trace-driven-tool-failure-recovery) |
| OpenSpec | [`trace-driven-tool-failure-recovery`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p3-trace-driven-tool-failure-recovery/openspec/changes/trace-driven-tool-failure-recovery) |

## 背景与真实问题

P1 能看到一次 Agent 执行，P2 能判断结果是否达标，但首次实操暴露了两个真实缺口：

1. AIOps 工具 Span 是在 LangGraph 节点结束后消费缓冲 SSE 时才创建，Span 耗时不是 SearchLog 的真实调用耗时。
2. MCP 失败后只能看到一个失败 Tool，无法区分首次尝试与内部重试；修复连接后也没有“保留失败证据、重新执行、再评测”的完整入口。

这类问题不依赖复杂的多 Agent 架构，却是接入 MCP、模型或外部 API 时经常遇到的工程痛点，适合在面试中从“发现问题—定位原因—设计边界—验证恢复”完整讲清楚。

## 实现闭环

```text
SearchLog 调用
  → 一个逻辑 Tool Audit + 一个 Tool Span
  → 每次 MCP 连接形成子 Attempt Span
  → 有界指数退避后成功，或 Job/Trace 明确失败
  → 失败页点击“重试本次诊断”
  → 创建新 Job（retryOfJobId 指向旧 Job）
  → 同一 Diagnostic Task 重新执行并创建新 Trace
  → 旧失败 Job/Trace 保留
  → Evaluation 使用失败 Trace 做负例、恢复 Trace 做正例
```

### 真实调用边界

- Tool Span 在 Executor 真正调用工具前创建，在工具返回或抛错时立即终结。
- `Attempt` Span 是 Tool Span 的子节点，保存尝试序号、最大次数、连接名称、状态和异常类别。
- Attempt observer 不接收原始异常正文；observer 自身失败也不会影响工具业务结果。
- 一个工具的内部重试仍只对应一个 Tool Audit 和一个 `tool` Span，因此评测的工具调用数不会虚增。

### 重试语义

- MCP 重试只重试一次连接/工具调用，使用 `retries + 1` 次上限和 0.2s 起步的指数退避。
- Job 重试重新执行整个诊断任务；只允许从 `failed` 或 `cancelled` Job 发起。
- Job 重试创建新 Job，保留 `retryOfJobId`；同一诊断资源每次执行创建新 Trace。
- 不覆盖原失败记录，不把一次失败“改写”为成功。

### Evaluation 验证

- 评测工作台不再只加载成功 Trace，选择项明确展示 Trace 状态。
- 一个 Case 可以暂存多条规则，再作为不可变 Dataset 版本提交。
- 新增 `p3-tool-recovery-pass.json`，离线验证恢复 Trace 的状态、输出、SearchLog、引用、耗时和逻辑工具数量。

## 关键决策

- **手动重试整个 Job，不做任意节点续跑**：当前状态和副作用边界不足以安全恢复任意 LangGraph 节点。
- **Attempt 是子 Span，不是 Tool Span**：保证调用数量、审计语义和父子关系一致。
- **只记录错误类别**：Trace 用于定位阶段，不复制供应商错误正文或可能含凭据的上下文。
- **复用通用 Background Job retry API**：减少 AIOps 专用状态机，保持文档索引任务和诊断任务的一致恢复语义。

## 验证证据

开发过程中的聚焦验证：

- MCP、Trace、AIOps 与 Evaluation 核心后端测试：17 passed。
- AIOps Store/组件测试：10 passed，TypeScript 检查通过。
- Evaluation 工作台测试：失败 Trace 加载与多规则 Case Builder 均通过。
- P3 离线 fixture 连续运行两次输出一致，Gate 通过且不含项目凭据。

发布前完整验证：

- 后端 Pytest：182 passed，1 skipped。
- 前端 Vitest：93 passed。
- API Contracts：27 passed。
- OpenSpec：47/47 items passed。
- Ruff 通过；Pyright：0 errors；合同与前端 TypeScript 检查通过。
- 前端生产构建通过，共转换 1,735 个模块；VitePress 文档构建通过。

真实 MCP 故障注入与恢复验收：

- 停止本机 MCP Server 后，Job、Trace 和 SearchLog Tool 均失败；Tool 下记录 2 个失败 Attempt。
- 恢复 MCP 后，关联 Job 成功，`retryOfJobId` 指向旧失败 Job；旧 Job 保持失败状态。
- 同一 Diagnostic Task 保留 2 条 Trace；恢复 Trace 的 SearchLog Tool 耗时 575ms，并记录 1 个成功 Attempt。
- 首版验收 Dataset 错把 `max_tool_calls` 设为 1，恢复 Gate 因实际存在 `knowledge_retrieval + SearchLog` 两个逻辑 Tool 而失败。由于 Dataset 不可变，创建修正版 v2 后复测：失败 Trace Gate failed（80 分），恢复 Trace Gate passed（100 分），通过率提升 100 个百分点。

这次规则修正本身也是闭环证据：Attempt 没有放大工具数，错误来自评测定义遗漏了 Planner 的知识检索工具。

## 安全、成本与范围边界

- 不在 Trace Attempt 中保存 URL、原始异常正文、工具参数、工具结果或凭据。
- Evaluation 回放已保存 Trace，不重新调用模型或 CLS。
- SearchLog 是只读查询，适合本版本的有限重试；创建工单等有副作用工具必须先设计幂等键，P3 未泛化实现。
- 后台 Runtime 仍与 FastAPI 同进程；进程崩溃可能中断正在运行的协程，租约只能帮助后续恢复领取，不等于分布式队列。

## 面试讲法

可以按以下顺序讲：

1. 实操时发现 Tool Span 耗时不可信，失败时也看不到每次 MCP 尝试。
2. 定位到 Span 在缓冲 SSE 消费阶段创建，而不是 Executor 的真实调用边界。
3. 将一个逻辑调用建模为 Tool，连接尝试建模为 Attempt 子 Span，避免工具数膨胀。
4. 复用持久 Job 创建关联重试，保留旧失败 Job/Trace，每次重跑生成新 Trace。
5. 用 P2 同一组规则分别绑定失败与恢复 Trace，证明修复不仅“程序跑完”，而且质量门禁通过。
6. 明确没有做任意节点续跑和副作用工具自动重试，因为当前缺少幂等与检查点安全保证。

## 查看与回退

```powershell
git fetch --tags origin
git switch --detach p3-trace-driven-tool-failure-recovery
```

如需从 P3 开始实验：

```powershell
git switch -c codex/review-p3 p3-trace-driven-tool-failure-recovery
```
