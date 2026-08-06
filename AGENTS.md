# 仓库指南

此仓库正在从零开始重建。在更改代码、编写 OpenSpec 提案或调整结构时，请遵循以下规则。

## 项目结构与模块组织

使用单一仓库结构：

```text
apps/backend/      # FastAPI、Pydantic v2、uv、pytest
apps/frontend/     # Vue 3、Vite、TypeScript
infra/             # docker-compose.yml 和 Dockerfile
openspec/          # OpenSpec 提案、规格与归档
docs/              # 规划与架构文档
```

后端代码必须在 `apps/backend/src/super_ai/` 下使用 src 布局。通过包名称导入，例如 `from super_ai.services.chat import ChatService`；绝不能从 `src.super_ai` 导入。

## 构建、测试和开发命令

- `openspec validate --all`：验证所有 OpenSpec 规格和变更。
- `uv run pytest`：在 `apps/backend` 运行后端测试。
- `uv run ruff check .`：运行 Python lint 检查。
- `uv run pyright`：运行 Python 类型检查。
- `docker compose -f infra/compose.yaml up`：启动本地基础设施栈。
- `npm run dev`：在 `apps/frontend` 启动 Vue 前端。

不要将 Poetry、PDM、pip-tools 或临时 shell 脚本作为主要工作流程。

## 编码风格与命名规范

Python 代码应为类型注解、依赖注入且与 Ruff 兼容。在模块导入期间不要连接到 SQLite、Milvus、LLMs 或 MCP 服务。在应用生命周期钩子、依赖提供者或显式初始化路径中创建外部资源。

仅使用 `langchain-openai` `ChatOpenAI` 和本地项目配置文件中的 OpenAI-compatible Qwen/Bailian 设置。应用程序代码不得读取本地机器的环境变量来获取项目配置。`config/project.json` 与 `config/user.project.json` 仅供本机使用并且必须被 Git 忽略；仓库只提交不含密钥的 `*.template.json`。不得提交模型密钥、CLS 凭据或其他真实凭据。

## 测试指南

使用 `pytest` 和 `pytest-asyncio`。核心仓库、服务、工具、API 合同、SSE 格式以及权限边界需要进行测试。不要删除测试或削弱检查以通过构建。

前端仅面向桌面 Web。除非用户后续明确提出，不新增移动端专用导航、抽屉、底部操作栏或移动端替代交互；前端验收以桌面浏览器为准。

## OpenSpec 工作流

每个功能必须作为一个专注的 OpenSpec 提案开始。当存在 `docs/openspec-feature-plan.md` 时，请遵循。每个提案必须包括验收测试或验证步骤。保持不相关功能的独立。

OpenSpec 的 proposal、design、tasks、spec、archive 以及相关 Markdown 文档默认使用简体中文撰写；函数名、配置键、API 路径、模型名、协议名和 OpenSpec 规范关键标题可以保留英文术语。

## 安全与集成约束

认证必须支持注册、登录和注销；永远不要存储明文密码。按 user 对知识库、聊天、AIOps、审计和向量搜索进行作用域划分。Milvus 仅存储向量知识数据，包含 owner/user/tenant 元数据，并进行权限过滤的检索。

MCP 集成必须使用真实工具和真实的腾讯 CLS 数据。不要提供模拟的个人资料、虚假的日志或不支持的 AIOps 结论。

## 提交与拉取请求指南

当前的历史记录使用了 Conventional Commits，例如 `chore: initialize openspec workflow`。使用简洁的提交信息，如 `feat: add chat service` 或 `test: cover sse contract`。PR 应包含目的、关联的 OpenSpec 变更、验证命令以及 UI 变更的截图。
