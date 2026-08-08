# 版本更新与复盘

本文件是项目版本历史的总入口。每个 P 版本都使用独立 Commit 和不可变 Tag 保存，并在
[`docs/version-history/`](docs/version-history/README.md) 中维护一份可复盘的详细记录。

## 版本总览

| 版本 | 日期 | 主题 | Commit | Tag | 详细复盘 |
| --- | --- | --- | --- | --- | --- |
| P3 | 2026-08-08 | Trace 驱动的外部工具失败恢复闭环 | 以不可变 Tag 指向为准 | [`p3-trace-driven-tool-failure-recovery`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p3-trace-driven-tool-failure-recovery) | [P3 复盘](docs/version-history/p3-trace-driven-tool-failure-recovery.md) |
| P2 | 2026-08-08 | 自动评测 Harness | [`f58cf18`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/f58cf18d815f66977ab3de7a2e62aca61733e128) | [`p2-agent-evaluation-harness`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p2-agent-evaluation-harness) | [P2 复盘](docs/version-history/p2-agent-evaluation-harness.md) |
| P1 | 2026-08-06 | 统一 Agent Trace | [`e3e7aac`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/e3e7aac9f009d37b4f5bc4f21007e05747f6c0a1) | [`p1-unified-agent-trace`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p1-unified-agent-trace) | [P1 复盘](docs/version-history/p1-unified-agent-trace.md) |
| P0 | 2026-08-06 | 工程展示底座 | [`b0c0937`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/b0c093789a5143215e04b0384f63e0136682db64) | [`p0-engineering-foundation`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p0-engineering-foundation) | [P0 复盘](docs/version-history/p0-engineering-foundation.md) |

## P3 同步归档的工程记录

- 建立版本复盘制度，补齐 P0、P1、P2 的详细复盘文档与统一模板。
- 修复 AIOps Tool Span 在缓冲 SSE 消费阶段才创建、耗时不能代表真实调用边界的问题。
- 新增 MCP Attempt、关联 Job 重试、失败/恢复 Trace 评测与无密钥 P3 fixture。

## 维护规则

每次发布新的 P 版本时必须同时完成：

1. 从 [`docs/version-history/template.md`](docs/version-history/template.md) 复制一份版本复盘文档。
2. 用真实的测试输出、Commit SHA 和变更范围填写记录，不使用记忆中的近似数据。
3. 更新上方版本总览，并把“尚未归入 P 版本”的内容归入新版本。
4. 创建独立 Conventional Commit 和注释 Tag，推送 `main` 与 Tag。
5. 核对本地 `HEAD`、Tag 指向和 GitHub 远端 SHA 一致。

详细流程见[版本历史维护说明](docs/version-history/README.md)。
