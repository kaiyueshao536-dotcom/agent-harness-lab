# P2：自动评测 Harness

## 版本信息

| 项目 | 内容 |
| --- | --- |
| 发布日期 | 2026-08-08 |
| 状态 | 已发布 |
| Commit | [`f58cf18`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/f58cf18d815f66977ab3de7a2e62aca61733e128) |
| Tag | [`p2-agent-evaluation-harness`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p2-agent-evaluation-harness) |
| OpenSpec | [`add-agent-evaluation-harness`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p2-agent-evaluation-harness/openspec/changes/add-agent-evaluation-harness) |
| 变更规模 | 45 个文件，3,770 行新增，5 行删除 |

## 背景与目标

P1 已经能回答“Agent 做了什么”，但还不能稳定回答“这次修改是否让 Agent 变好”。如果每次只能人工打开 Trace 判断结果，回归成本高、结论难复现，也无法在 CI 中阻止明显退化。

P2 的目标是以 P1 的真实 Trace 为评测对象，建立版本化数据集、确定性评分、质量门禁、基线比较和自动化报告，使 Agent 修改能够被重复验证。

## 实现内容

### 评测数据与权限

- 新增不可变的版本化数据集、案例、运行和逐案例结果模型。
- 新增 Alembic 迁移、仓储协议与 SQLite 实现。
- 数据集、运行、Trace 和基线均按 owner 校验；跨用户资源对外表现为 404。
- 基线必须属于同一用户和同一数据集，案例结果必须绑定该数据集中的 Trace。

### 确定性评分

- 建立封闭的 Pydantic 规则模型和无外部依赖的纯评分内核。
- 支持文本、工具调用、引用数量、耗时、工具数量和 Trace 状态等规则。
- 使用等权、可重复计算的案例分数，聚合通过率、平均分和质量门禁。
- 支持同数据集候选运行与基线运行比较，展示通过率、分数、耗时和工具数量变化。
- 输出摘要限制为 500 字符，并对常见 Key、Token 和密码模式脱敏。

### Trace-backed 运行

- Chat 案例从 Trace 对应的助手结果解析观察值。
- AIOps 案例从报告、证据链和工具 Span 解析观察值。
- 评测复用已经保存的 Trace，不重新请求模型或腾讯云 CLS，因此离线复盘本身不产生新的模型/CLS 调用费用。

### API 与桌面工作台

- 新增评测数据集和运行的创建、列表、详情 API。
- 新增 TypeScript 合同、OpenAPI schema、Pydantic 请求模型和统一错误语义。
- 新增“自动评测”桌面入口，可创建数据集、绑定 Trace、选择规则、运行门禁、对比基线并跳转原 Trace。
- 报告展示聚合指标、失败检查、逐案例安全摘要和基线差异。

### CLI 与 CI

- 新增 `super-ai-eval` 离线 CLI，严格校验 JSON fixture。
- 退出码约定：`0` 门禁通过、`1` 门禁失败、`2` 输入无效。
- 新增通过/失败 fixture，并把通过用例加入 GitHub Actions。
- CLI 不需要数据库、模型、网络或云服务密钥。

## 关键设计决策

- **先做确定性规则，而不是直接引入 LLM-as-a-Judge**：保证 CI 可复现、无额外成本，并让失败原因可解释。
- **绑定真实 Trace，而不是复制结果正文**：复用 P1 的观测底座，减少敏感数据扩散和多份数据不一致。
- **数据集发布后不可变**：保证历史运行和基线比较始终指向同一评测定义；需要调整时创建新版本。
- **跨用户资源统一 404**：既满足隔离，又避免通过错误差异枚举其他用户数据。
- **前端报告提供 Trace 跳转**：评测负责发现退化，Trace 负责解释退化，形成闭环。

## 关键文件

- [`apps/backend/src/super_ai/evaluation/service.py`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p2-agent-evaluation-harness/apps/backend/src/super_ai/evaluation/service.py)
- [`apps/backend/src/super_ai/evaluation/scoring.py`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p2-agent-evaluation-harness/apps/backend/src/super_ai/evaluation/scoring.py)
- [`apps/backend/src/super_ai/evaluation/cli.py`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p2-agent-evaluation-harness/apps/backend/src/super_ai/evaluation/cli.py)
- [`apps/backend/src/super_ai/memory/evaluation_sqlite.py`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p2-agent-evaluation-harness/apps/backend/src/super_ai/memory/evaluation_sqlite.py)
- [`apps/frontend/src/views/EvaluationView.vue`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p2-agent-evaluation-harness/apps/frontend/src/views/EvaluationView.vue)
- [`packages/api-contracts/src/evaluations.ts`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p2-agent-evaluation-harness/packages/api-contracts/src/evaluations.ts)
- [`docs/evaluation-harness.md`](../evaluation-harness.md)
- [`openspec/changes/add-agent-evaluation-harness/`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p2-agent-evaluation-harness/openspec/changes/add-agent-evaluation-harness)

## 验证结果

发布前完整验证结果：

- 后端 Pytest：177 passed，1 skipped。
- 前端 Vitest：90 passed。
- API Contracts：27 passed。
- 前端生产构建通过，共转换 1,735 个模块。
- Ruff 通过。
- Pyright：0 errors。
- OpenSpec 严格校验通过，23/23 tasks 完成。
- `p2-smoke-pass.json` 离线 CLI 门禁通过。
- 敏感模式扫描和 `git diff --check` 通过。

本机命令输出包含与项目无关的 Conda `typing_extensions` 警告，以及 OpenSpec PostHog 上报超时；两者不影响命令退出码和项目验证结果。

## 安全与成本边界

- 不保存完整提示词、思维链、原始工具输入输出或云服务凭据。
- 评测结果只持久化安全摘要、指标、规则检查和 Trace 标识。
- 常规 CLI/CI 评测离线运行，不调用 Qwen、CLS 或其他付费服务。
- 只有生成新的真实 Trace 时，原 Chat/AIOps 执行链路才可能调用用户配置的模型或 CLS。

## 已知限制

- 当前规则是确定性工程规则，尚未包含语义正确性 Judge。
- 当前 runner 评测已存在 Trace，不负责批量在线重放真实 Agent 请求。
- 适合本地和单实例评测；大规模异步评测队列尚未实现。
- 数据集发布后不能编辑，需要创建新版本表达规则或案例变化。

## 复盘结论

P2 把 Trace 从“可观察数据”转化为“可执行质量资产”。项目由此形成 `执行 → Trace → 评测 → 门禁 → 回到 Trace 排障` 的工程闭环，这比只展示 Agent 能回答问题更能证明 Harness Engineering、质量治理和可维护性能力。

下一步如果引入 LLM-as-a-Judge 或 live runner，应保留当前确定性规则作为低成本基础门禁，并把 Judge 结果作为额外信号，而不是替换现有可复现检查。

## 查看与回退

```powershell
git fetch --tags origin
git switch --detach p2-agent-evaluation-harness
```

如需从 P2 开始实验：

```powershell
git switch -c codex/review-p2 p2-agent-evaluation-harness
```
