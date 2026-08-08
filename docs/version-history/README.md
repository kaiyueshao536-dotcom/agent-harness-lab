# 版本历史维护说明

这个目录保存可用于项目复盘、面试讲解和问题追踪的版本记录。根目录
[`CHANGELOG.md`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/main/CHANGELOG.md) 负责快速导航，本目录中的文件负责解释每个版本为什么做、
具体做了什么、如何验证，以及当时还存在哪些限制。

## 当前版本

- [P3.3.1：Evaluation 跨 Dataset 运行草稿隔离](p3.3.1-evaluation-binding-reset.md)
- [P3.3：AIOps RAG 证据角色隔离](p3.3-rag-evidence-isolation.md)
- [P3.2：恢复执行与报告证据边界闭环](p3.2-recovery-evidence-quality.md)
- [P3.1：手工验收缺口闭环](p3.1-manual-acceptance-gap-closure.md)
- [P0：工程展示底座](p0-engineering-foundation.md)
- [P1：统一 Agent Trace](p1-unified-agent-trace.md)
- [P2：自动评测 Harness](p2-agent-evaluation-harness.md)
- [P3：Trace 驱动的外部工具失败恢复闭环](p3-trace-driven-tool-failure-recovery.md)

## 信息来源与可信度

版本记录按以下优先级取证：

1. Git Commit、Tag 和实际 Diff。
2. 对应 OpenSpec 的 proposal、design、specs 和 tasks。
3. 测试、构建、类型检查和静态检查的真实输出。
4. README、架构文档和讨论记录。

如果文档描述与代码冲突，以对应 Tag 中的代码和测试为准，并在当前 `main` 修正文档，不移动旧 Tag。

## 每次更新的操作流程

1. 开始开发前创建或确认聚焦的 OpenSpec 变更。
2. 开发过程中把重要的范围调整和工程决策写入 design/tasks，而不是只保留在对话中。
3. 完成后运行与风险相匹配的完整验证，并保留准确结果。
4. 复制 [`template.md`](template.md)，建立 `pN-主题.md` 复盘文件。
5. 更新根目录 [`CHANGELOG.md`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/main/CHANGELOG.md) 和 README 入口。
6. 创建一个独立 Commit，并创建注释 Tag，例如 `p3-...`。
7. 推送 Commit 和 Tag 后，用 `git ls-remote` 核对远端。

## 编写要求

- 记录“为什么做”和“没有做什么”，避免只罗列文件。
- 测试数量只写真实输出；无法核实时记录命令和“已通过”，不要猜测数字。
- 明确区分真实能力、演示能力和未来路线图。
- 不写入 API Key、CLS 凭据、用户数据、原始日志或本机私有配置。
- 旧 Tag 不移动、不覆盖；文档纠错使用新的 docs Commit。
