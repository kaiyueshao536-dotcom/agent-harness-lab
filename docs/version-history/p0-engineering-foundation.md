# P0：工程展示底座

## 版本信息

| 项目 | 内容 |
| --- | --- |
| 发布日期 | 2026-08-06 |
| 状态 | 已发布 |
| Commit 范围 | `d50ced3` 至 `b0c0937` |
| 版本锚点 | [`b0c0937`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/commit/b0c093789a5143215e04b0384f63e0136682db64) |
| Tag | [`p0-engineering-foundation`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p0-engineering-foundation) |
| OpenSpec | [`prepare-public-project-foundation`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p0-engineering-foundation/openspec/changes/prepare-public-project-foundation) |
| 基线规模 | 853 个文件，71,307 行新增 |

> P0 是首次把既有工程整理并发布为公共 Git 基线，因此规模统计包含完整项目导入，不能理解为这个阶段新编写了 71,307 行代码。

## 背景与目标

原项目具备较多 Agent、AIOps、RAG 和 MCP 能力，但缺少适合公开审阅的工程入口。P0 的目标不是新增业务功能，而是让招聘方或协作者能够安全地找到项目、理解项目、启动项目并验证项目。

成功标准包括：仓库无真实凭据、公开说明完整、CI 无密钥运行、代码结构可审阅、GitHub 可以稳定访问和回退。

## 实现内容

### 公共仓库与安全卫生

- 建立 `.gitignore`、`.dockerignore` 和仓库属性规则，排除本地配置、数据库、日志、缓存、构建产物和个人材料。
- 只提交不含密钥的配置模板；真实 `config/project.json` 与 `config/user.project.json` 保持本机私有。
- 增加 `LICENSE`、`SECURITY.md`、`CONTRIBUTING.md`、Issue 模板、PR 模板和 Dependabot 配置。

### 工程展示

- 重写根 README，说明项目定位、架构、能力、演示链路、快速开始、验证命令、安全边界和路线图。
- 增加英文架构概览与 Windows、macOS、Linux 安装说明。
- 明确真实 CLS/MCP 边界，不使用虚假日志或伪造诊断结论冒充集成结果。

### 持续集成

- 建立 GitHub Actions 无密钥 CI。
- CI 覆盖 OpenSpec、Python lint/类型/测试、TypeScript 合同、前端类型/测试/构建。
- 通过非敏感测试占位配置和运行目录准备，使 CI 不依赖本机密钥。

### 模块边界

- 拆分 FastAPI 路由装配和 AIOps 工作流内部边界。
- 保留 `super_ai.api.app:create_app`、既有 API、SSE 和持久化行为，降低结构调整对产品功能的影响。

## P0 提交序列

| Commit | 内容 |
| --- | --- |
| `d50ced3` | 建立公共项目基础和首次 Git 基线 |
| `011bdf2` | 记录公开工程基线 |
| `3b0f495` | 准备无密钥 CI 配置 |
| `b91f78b` | 注入非敏感测试占位配置 |
| `ace99f6` | 创建 CI 运行时数据目录 |
| `b0c0937` | 完成 OpenSpec 任务并发布 P0 锚点 |

## 关键设计决策

- **不把本机环境变量作为业务配置源**：项目配置使用被 Git 忽略的本地 JSON，仓库只保存模板。
- **CI 不连接真实云服务**：常规质量门禁必须可离线、无密钥复现，真实 Qwen、CLS 和 Milvus 集成由显式本地配置启用。
- **先建立可信展示，再增加新能力**：P0 固化工程底座，为后续 Trace 和评测版本提供可比较的起点。

## 关键文件

- [`README.md`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p0-engineering-foundation/README.md)
- [`.github/workflows/ci.yml`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p0-engineering-foundation/.github/workflows/ci.yml)
- [`CONTRIBUTING.md`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p0-engineering-foundation/CONTRIBUTING.md)
- [`SECURITY.md`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/blob/p0-engineering-foundation/SECURITY.md)
- [`docs/architecture.en.md`](../architecture.en.md)
- [`openspec/changes/prepare-public-project-foundation/`](https://github.com/kaiyueshao536-dotcom/agent-harness-lab/tree/p0-engineering-foundation/openspec/changes/prepare-public-project-foundation)

## 验证结果

P0 OpenSpec 任务记录确认以下门禁通过：

- `openspec validate --all`
- 后端 Ruff、Pyright、Pytest
- 前端类型检查、测试和构建
- 公开文件、文件名和敏感模式审计
- GitHub `main` 推送与 CI 远端确认

当时没有保留可靠的逐套件通过数量，因此本复盘不补写推测数字。

## 已知限制

- Chat 与 AIOps 还没有统一的 Agent Trace/Span 模型。
- 缺少面向执行过程的统一检索和桌面时间线。
- 缺少基于真实 Trace 的自动回归评测。

这些问题分别成为 P1 和 P2 的直接输入。

## 复盘结论

P0 把“本机能运行的项目”转换成了“第三方能够安全审阅和验证的工程项目”。它主要证明工程治理、仓库卫生、可复现性和公开协作能力，而不是新的 Agent 算法能力。

## 查看与回退

```powershell
git fetch --tags origin
git switch --detach p0-engineering-foundation
```

如需从 P0 开始实验：

```powershell
git switch -c codex/review-p0 p0-engineering-foundation
```
