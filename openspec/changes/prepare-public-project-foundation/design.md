## Context

项目已经具备 FastAPI、Vue、LangChain/LangGraph、MCP、SQLite、Milvus 和较完整的自动化测试，但当前工作区没有 Git 元数据，也没有 GitHub CI 与公开协作文件。本地目录还包含真实配置、缓存、虚拟环境、运行时日志、数据库和个人材料。后端 `api/app.py` 与 `aiops/diagnostics.py` 集中了大量装配和业务逻辑，不利于公开审阅与后续 Trace/Evaluation Harness 扩展。

本变更面向招聘展示、外部贡献者和后续 Agent Harness 开发。必须遵守项目配置不读取环境变量、真实凭据不提交、真实 MCP/CLS 结论不伪造以及公共 API/SSE 合同保持兼容的约束。

## Goals / Non-Goals

**Goals:**

- 形成可安全公开的 Git 跟踪集合和可审计的首次提交。
- 让 GitHub CI 在无真实外部凭据时完成所有静态检查与自动化测试。
- 让首次访问者在 README 首页理解项目价值、架构、快速开始、验证方式和能力边界。
- 用清晰模块边界降低后端入口与 AIOps 工作流的维护成本，同时保持现有行为。
- 提供标准开源协作、安全披露和贡献入口。

**Non-Goals:**

- 不在本变更中实现 Agent Trace、自动评测、多 Agent 或 Coding/Test Agent。
- 不把真实 Qwen、CLS 或其他服务凭据迁移到 GitHub Actions。
- 不重写现有业务算法、API、SSE 事件、数据库模型或前端交互。
- 不伪造历史提交或创建虚假的开源贡献记录。

## Decisions

### 使用单一公共仓库展示完整单体仓库

在 `kaiyueshao536-dotcom/agent-harness-lab` 下发布当前 monorepo，而不是拆分前后端仓库。单仓能完整展示 OpenSpec、共享合同、基础设施和端到端质量门禁，也更符合 Harness Engineering 的系统性叙事。

备选方案是只公开核心 Agent 代码，但会丢失平台工程、权限、前端与基础设施证据，因此不采用。

### 普通 CI 完全无密钥

GitHub Actions 只运行 OpenSpec、静态检查、单元/合同测试和前端构建。测试通过依赖注入隔离 LLM、MCP、Milvus 和 CLS；真实集成验证继续由显式本地流程执行。这样来自 fork 的 PR 也能安全运行，不需要向不受信任代码暴露 Secrets。

备选方案是在普通 CI 中配置云凭据，但存在 fork/日志泄漏风险且增加不稳定外部依赖，因此不采用。

### 公开展示文档以根 README 为入口

根 README 使用简体中文为主，并提供英文摘要和英文架构文档入口。首页只陈述已实现能力，将未来 Trace、Evaluation 和多 Agent 放入 Roadmap。架构图使用 Mermaid，避免依赖外部图片托管。

### 模块化采用行为保持型抽取

先抽取路由注册、依赖提供和 LangGraph 节点/辅助边界，保留 `create_app` 工厂、原路径、响应结构和依赖注入接口。每次抽取后运行现有测试；不在同一变更中优化算法或更改数据模型。

备选方案是一次性重写为新架构，但回归面过大且难以区分结构变化与功能变化，因此不采用。

### Git 发布以真实基线提交开始

若不存在原始 `.git`，初始化新仓库并以 Conventional Commit 创建真实基线。提交邮箱优先采用 GitHub noreply；如果无法从已认证账户解析 noreply 地址，则沿用用户已配置的本地身份。发布前检查 Git 索引、忽略项和敏感模式，不删除用户的本地文件。

## Risks / Trade-offs

- [敏感值被正则漏检] → 同时检查忽略规则、暂存文件列表、模板内容和常见凭据模式；只推送 Git 索引内容。
- [无密钥 CI 与真实运行存在差异] → 保留清晰的手动真实集成验收文档，并将普通 CI 定位为可重复质量门禁。
- [大文件拆分引入循环导入] → 保持依赖方向为 API 装配到领域服务，使用现有 Protocol/依赖提供边界并逐步运行类型检查。
- [公开仓库名称或可见性需要调整] → 远端名称可在 GitHub 重命名，Git remote 可无损更新；本地工作不依赖远端创建成功。
- [Windows 与 Linux CI 行为差异] → GitHub Actions 使用 Ubuntu 验证可移植性，本地继续运行 Windows 验证。

## Migration Plan

1. 扩展忽略规则并新增公开前审计测试，确保本地文件不进入索引。
2. 新增 CI、许可证、贡献、安全和 GitHub 模板。
3. 更新 README 与架构文档，并验证所有链接和命令。
4. 分阶段抽取后端模块，保持导入入口和公共行为不变。
5. 运行 OpenSpec、后端与前端全量验证。
6. 初始化 Git、检查暂存集合、提交基线、创建并推送公共仓库。

若模块化验证失败，回退相应抽取而保留仓库卫生、CI 和文档改进；若远端发布失败，本地 Git 基线和全部工程资产仍然可用。

## Open Questions

- GitHub CLI 当前未安装；远端创建阶段需要使用已认证的替代方式、安装 CLI，或由用户完成一次网页登录授权。
- 公共仓库首次发布后是否立即创建 `v0.1.0` Release，可在 P0 推送成功后决定。
