## Why

当前工作区尚未建立可公开审阅的 Git/GitHub 工程基线，缺少持续集成、开源协作元数据和面向招聘方的可复现项目入口；同时后端装配与 AIOps 工作流集中在超大模块中，削弱了项目对工程质量、可维护性和 Harness Engineering 能力的证明。现在需要在不改变现有 API 与产品行为的前提下，建立可安全公开、可自动验证、可快速理解的项目展示底座。

## What Changes

- 扩展仓库卫生规则，排除真实配置、本地运行时、缓存、构建产物、数据库、日志、个人简历和非项目私有材料，并在公开前执行文件名与敏感模式审计。
- 新增 GitHub Actions 持续集成，在无真实模型或 CLS 凭据的环境中验证 OpenSpec、后端 lint/类型/测试以及前端类型/测试/构建。
- 新增许可证、贡献指南、安全策略、Issue/PR 模板和面向公开展示的中英文项目入口。
- 重写根 README，突出 Agent Runtime、LangGraph、MCP、Skill、记忆、证据链和持久任务，并提供架构、快速开始、验证命令、演示流程、限制与路线图。
- 在保持路由、依赖注入、SSE 与持久化行为不变的情况下，拆分后端应用装配和 AIOps 工作流的模块边界，降低单文件复杂度。
- 初始化真实 Git 历史起点，并在验证通过后发布到 `kaiyueshao536-dotcom/agent-harness-lab` 公共仓库。

## Capabilities

### New Capabilities

- `continuous-integration`: 定义 GitHub 持续集成对 OpenSpec、后端和前端质量门禁的要求。
- `public-project-showcase`: 定义公开仓库必须提供的项目定位、架构、快速开始、协作、安全与演示材料。

### Modified Capabilities

- `repo-hygiene`: 扩展公开仓库对缓存、运行时数据、个人材料和敏感信息审计的要求。
- `project-foundation`: 要求后端 API 与 Agent 工作流保持清晰模块边界，同时维持现有公共合同和验证路径。

## Impact

- 影响根目录工程文件、`.gitignore`、GitHub workflow、README 与 `docs/` 展示文档。
- 影响 `apps/backend/src/super_ai/api/` 和 `apps/backend/src/super_ai/aiops/` 的内部模块组织，但不引入 API、SSE 或存储格式破坏性变更。
- 新增公共 GitHub 仓库和 CI 执行环境；真实 Qwen/CLS 凭据与真实用户数据不进入仓库或普通 CI。
