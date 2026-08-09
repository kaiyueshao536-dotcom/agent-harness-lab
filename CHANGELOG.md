# 版本更新与复盘

本文件是项目版本历史的总入口。每个 P 版本都使用独立 Commit 和不可变 Tag 保存，并在
[`docs/version-history/`](docs/version-history/README.md) 中维护一份可复盘的详细记录。

## 版本总览

| 版本 | 日期 | 主题 | Commit | Tag | 详细复盘 |
| --- | --- | --- | --- | --- | --- |
| P5 | 2026-08-09 | Chat 记忆与上下文生命周期闭环 | 以不可变 Tag 指向为准 | `p5-chat-memory-lifecycle` | [P5 复盘](docs/version-history/p5-chat-memory-lifecycle.md) |
| P4 | 2026-08-09 | AIOps 上下文路由、Token 预算与质量 Gate | 以不可变 Tag 指向为准 | `p4-aiops-context-quality` | [P4 复盘](docs/version-history/p4-context-quality.md) |
| P3.3.1 | 2026-08-09 | Evaluation 跨 Dataset 运行草稿隔离 | 以不可变 Tag 指向为准 | `p3.3.1-evaluation-binding-reset` | [P3.3.1 复盘](docs/version-history/p3.3.1-evaluation-binding-reset.md) |
| P3.3 | 2026-08-09 | AIOps RAG 证据角色隔离 | 以不可变 Tag 指向为准 | [`p3.3-rag-evidence-isolation`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p3.3-rag-evidence-isolation) | [P3.3 复盘](docs/version-history/p3.3-rag-evidence-isolation.md) |
| P3.2 | 2026-08-09 | 恢复执行与报告证据边界闭环 | 以不可变 Tag 指向为准 | [`p3.2-recovery-evidence-quality`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p3.2-recovery-evidence-quality) | [P3.2 复盘](docs/version-history/p3.2-recovery-evidence-quality.md) |
| P3.1 | 2026-08-08 | 手工验收缺口闭环 | 以不可变 Tag 指向为准 | [`p3.1-manual-acceptance-gap-closure`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p3.1-manual-acceptance-gap-closure) | [P3.1 复盘](docs/version-history/p3.1-manual-acceptance-gap-closure.md) |
| P3 | 2026-08-08 | Trace 驱动的外部工具失败恢复闭环 | 以不可变 Tag 指向为准 | [`p3-trace-driven-tool-failure-recovery`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p3-trace-driven-tool-failure-recovery) | [P3 复盘](docs/version-history/p3-trace-driven-tool-failure-recovery.md) |
| P2 | 2026-08-08 | 自动评测 Harness | [`f58cf18`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/f58cf18d815f66977ab3de7a2e62aca61733e128) | [`p2-agent-evaluation-harness`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p2-agent-evaluation-harness) | [P2 复盘](docs/version-history/p2-agent-evaluation-harness.md) |
| P1 | 2026-08-06 | 统一 Agent Trace | [`e3e7aac`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/e3e7aac9f009d37b4f5bc4f21007e05747f6c0a1) | [`p1-unified-agent-trace`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p1-unified-agent-trace) | [P1 复盘](docs/version-history/p1-unified-agent-trace.md) |
| P0 | 2026-08-06 | 工程展示底座 | [`b0c0937`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/b0c093789a5143215e04b0384f63e0136682db64) | [`p0-engineering-foundation`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p0-engineering-foundation) | [P0 复盘](docs/version-history/p0-engineering-foundation.md) |

## P3 同步归档的工程记录

- 建立版本复盘制度，补齐 P0、P1、P2 的详细复盘文档与统一模板。
- 修复 AIOps Tool Span 在缓冲 SSE 消费阶段才创建、耗时不能代表真实调用边界的问题。
- 新增 MCP Attempt、关联 Job 重试、失败/恢复 Trace 评测与无密钥 P3 fixture。

## P3.1 手工验收闭环

- 失败任务即使已有降级报告，也保留“重试本次诊断”入口。
- Trace 时间线根据 `parentSpanId` 展示 Tool/Attempt 层级、尝试序号、上限和错误类别。
- 统一公开报告序列化边界，历史内容在返回浏览器前脱敏内部 URL、Topic ID 和密钥模式。
- 禁用的告警源不再阻断已启用的本地 Alertmanager；空告警返回正常空状态。
- 真实重试保留旧失败 Job/Trace，并创建关联的成功 Job 与成功 Trace。

## P3.2 恢复证据质量闭环

- 将同一诊断任务的累计步骤和工具调用按独立 Trace 分组，明确“跨 N 次执行累计”和单次执行指标。
- 历史案例正文只供 Planner 参考，不再进入 Report 的当前事实输入。
- 工具失败或 SearchLog 零结果使用确定性谨慎报告，不把无匹配日志直接推断为 Topic 无数据或采集链路异常。
- 修复 Topic ID 脱敏占位符的重复右括号，并新增 `evidence_cautious` 离线确定性评测规则。
- 用真实的两次失败、一次恢复 Trace 和 P2 Gate 完成手工复测；详细数据见 P3.2 复盘。

## P3.3 AIOps RAG 证据角色隔离

- Planner 默认只检索正式 SOP，在 Rerank 前排除历史 `diagnostic-case` 和普通文档。
- SOP 上传与索引补齐 incident、alert、service、sopId 等受控元数据，同时保持服务器 owner/tenant 边界。
- Planner 持久化安全的 retrieval Context Snapshot，前端可解释检索策略、来源角色、分数和退化原因。
- 混合语料测试与 P3.3 离线 Gate 将真实历史污染问题转为可重复防回归检查。
- 发布后使用真实支付告警 Trace 创建 P3.3 专用不可变 Dataset；4 类确定性规则全部通过，报告中的 5 个已知历史污染词均未出现。

## P3.3.1 Evaluation 跨 Dataset 运行草稿隔离

- 修复创建新 Dataset 后仍提交旧 Case Trace 绑定和旧 Baseline 的前端状态泄漏。
- Dataset 创建与切换统一调用运行草稿清理；候选版本标签保留，后端精确绑定校验不放宽。
- 增加真实复现顺序的组件测试，证明新 Dataset 首次运行只提交新 Case ID。

## P4 AIOps 上下文质量闭环

- 在 SOP-only 结果上按告警与服务元数据确定性路由，冲突 SOP 不再进入 Planner；上下文限制为 3 个来源和 1600 近似 Token。
- `sop-budget-v1` Context Snapshot 与执行链展示候选、亲和度、选中/排除原因和预算，同时兼容旧 Snapshot。
- Evaluation 增加必需来源、禁止来源和最大上下文 Token 规则，并提供无密钥 P4 离线 fixture。
- 真实验收首次发现旧 Milvus 索引缺少路由元数据；重新 seed/reindex 后，上下文从 3 个来源/872 Token 降至 1 个来源/284 Token。
- 同一不可变 Dataset 中，修复前 Trace Gate 失败（80%），修复后 Trace Gate 通过（100%）；平均分相对 Baseline 提升 20 个百分点。

## P5 Chat 记忆与上下文生命周期闭环

- 将长对话真实审计中的压缩观测黑洞、推断污染、回答重复和失败丢消息纳入一个受控闭环。
- 结构化 Memory Snapshot 区分当前与已废止事实，通过 message id 和原文包含校验拒绝无来源候选。
- Trace 在压缩前创建，展示 prepare/compact/attempt/validate/agent；压缩有界超时和重试，失败不推进边界。
- 用户消息先落库，失败后使用同一 message id 恢复；桌面 Memory Inspector 展示快照、来源和重试入口。
- Evaluation 新增 6 类 Memory 规则，A—D 离线 fixture 的 Gate、通过率和平均分均为 100%。

## 维护规则

每次发布新的 P 版本时必须同时完成：

1. 从 [`docs/version-history/template.md`](docs/version-history/template.md) 复制一份版本复盘文档。
2. 用真实的测试输出、Commit SHA 和变更范围填写记录，不使用记忆中的近似数据。
3. 更新上方版本总览，并把“尚未归入 P 版本”的内容归入新版本。
4. 创建独立 Conventional Commit 和注释 Tag，推送 `main` 与 Tag。
5. 核对本地 `HEAD`、Tag 指向和 GitHub 远端 SHA 一致。

详细流程见[版本历史维护说明](docs/version-history/README.md)。
