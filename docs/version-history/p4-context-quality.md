# P4：AIOps 上下文质量闭环

## 版本信息

| 项目 | 内容 |
| --- | --- |
| 发布日期 | 2026-08-09 |
| 状态 | 已发布 |
| Commit | 以发布 Tag 的不可变指向为准 |
| Tag | `p4-aiops-context-quality` |
| OpenSpec | `openspec/changes/optimize-aiops-context-quality/` |

## 背景与目标

P3.3 解决了历史诊断案例污染，但真实支付告警的 SOP-only Top 3 仍包含搜索 ES 等其他服务 SOP。P4 要在不引入通用记忆平台或 LLM Judge 的前提下，以确定性元数据路由、Token 预算、可解释 Snapshot 和 Trace-backed Gate 闭环这个问题。

## 实现内容

- 新增独立 SOP 上下文选择器，按告警、服务、通用和冲突四类亲和度排序与过滤。
- Planner 检索 5 个候选，最多向模型发送 3 个来源和 1600 个近似 Token；第一来源支持预算内截断。
- `sop-budget-v1` Snapshot 记录候选、选中/排除原因、估算与使用 Token，不保存正文和 Prompt。
- 执行链显示候选数、实际来源、预算和每个候选决策，并兼容旧 `sop-only` Snapshot。
- Evaluation 增加必需来源、禁止来源和最大上下文 Token 三类规则；从 owner 范围 Planner step 解析观察值。
- 增加无密钥 P4 CLI fixture、选择器/诊断/评分/服务/合同/前端回归测试。

## 关键设计决策

- **元数据优先于相似度阈值**：冲突来源即使语义分数高也不能作为当前上下文。
- **旧数据保持可用但明确标为 generic**：避免升级直接让所有旧 SOP 不可用；严格路由需要显式 reindex。
- **固定预算而非追求精确账单 Token**：本版本控制相对上下文体量，使用可测试的 LangChain 近似计数。
- **确定性 Gate 而非 LLM Judge**：规则可解释、可离线复现，适合当前项目规模。

## 关键文件

- `apps/backend/src/super_ai/aiops/context_quality.py`
- `apps/backend/src/super_ai/aiops/diagnostics.py`
- `apps/backend/src/super_ai/evaluation/`
- `apps/frontend/src/components/AiopsEvidenceChain.vue`
- `apps/frontend/src/views/EvaluationView.vue`
- `evals/fixtures/p4-context-quality-pass.json`
- `docs/learning/p4-context-quality.md`

## 真实验收结果

发布前验证结果：

- 后端共收集 199 项测试：198 项执行并通过，1 项因 Windows 不具备原生 POSIX bash 而按预期跳过。
- Ruff 通过；Pyright 为 0 个错误、0 个警告。
- 前端 27 个测试文件、100 项测试全部通过；共享合同 27 项测试通过。
- 前端生产构建、共享合同类型检查和 VitePress 文档构建通过。
- P4 无密钥离线 Gate：通过率 100%、平均分 100%，5 条规则全部通过。
- `openspec validate --all`：52 项通过、0 项失败。

全量 pytest 仍输出既有 `aiosqlite` 测试线程在事件循环关闭后的资源告警，但命令退出码为 0；OpenSpec 退出时还出现不影响校验结果的 Anaconda 插件与 PostHog 网络告警。

第一次运行 `trace_210491db40664bc0a501fdf22cddaff4` 暴露旧索引缺少路由元数据：候选 5、进入 3、使用 872 Token，搜索 ES SOP 错误进入；P4 Gate 平均分 80%，Gate 失败。

重新 seed/reindex 10 份 Java 电商 SOP 后，`trace_224e144cd4654e8bb444c1bd364a91e9` 得到：

- 候选 5、实际进入 1；支付超时 SOP 为 `alert-match`；4 个其他服务 SOP 为 `metadata-conflict`。
- 上下文使用 284/1600 近似 Token，比修复前减少 588（约 67.4%）。
- `knowledge_retrieval` 与真实 CLS `SearchLog` 均成功，2 次工具调用，端到端耗时 114,723 ms。
- 不可变 Dataset `P4 AIOps 上下文质量回归集 v1` 的 5 条规则全部通过，平均分 100%。
- 相对失败 Baseline：通过率 +100 pt、平均分 +20 pt、耗时 -2.6988%、工具调用变化 0。

## 安全与成本边界

- 上下文选择和离线 fixture 不调用外部服务；真实验收调用现有模型、Milvus、MCP 与 CLS，可能产生相应用量。
- Snapshot 与 Evaluation 仅保存安全来源名、决策和聚合 Token，不保存知识正文、Prompt、凭据、MCP URL 或 Topic ID。
- 所有检索、Planner step 和 Evaluation Trace 读取继续按 owner 范围执行。

## 已知限制

- 元数据缺失的旧 SOP 会作为 `generic` 保留，必须 reindex 才能获得严格冲突过滤。
- 近似 Token 不等于供应商计费 Token，也未覆盖系统提示词、告警和工具 Schema 的全部上下文成本。
- 当前策略只处理 SOP 上下文；不实现长对话记忆治理、案例辅助规划或通用多 Agent 上下文同步。
- 真实诊断耗时仍受模型延迟影响，本次两条 Trace 为 117,905 ms 和 114,723 ms。

## 复盘结论

P4 的价值不只是增加一个过滤器，而是完整暴露并关闭了第二层问题：新代码正确不代表存量索引已经迁移。通过 Snapshot 取证、失败 Gate、显式 reindex、成功 Trace 和 Baseline 对比，项目展示了从数据、运行时到评测的真实问题闭环。

## 查看与回退

```powershell
git fetch --tags origin
git switch --detach p4-aiops-context-quality
```

如需基于本版本继续实验：

```powershell
git switch -c codex/review-p4 p4-aiops-context-quality
```
