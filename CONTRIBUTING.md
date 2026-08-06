# 贡献指南

感谢你关注 Agent Harness Lab。本项目使用 OpenSpec 管理功能变更，并要求所有提交保持可测试、可审阅且不包含真实凭据。

## 开始之前

1. 阅读根目录 `README.md`、`AGENTS.md` 和相关 `openspec/specs/`。
2. 对功能或合同变更，先创建一个聚焦的 OpenSpec change，并写明验收步骤。
3. 从 `config/*.template.json` 复制本地配置；不要提交 `config/project.json` 或 `config/user.project.json`。
4. 不要提交模型密钥、CLS 凭据、真实用户数据、运行日志或本地数据库。

## 本地验证

```text
npx openspec validate --all

cd apps/backend
uv sync
uv run ruff check .
uv run pyright
uv run pytest

cd ../frontend
npm run typecheck
npm run test
npm run build
```

## 提交与 Pull Request

- 使用 Conventional Commits，例如 `feat: add agent trace model`、`test: cover tool timeout`。
- 一个 Pull Request 只解决一个聚焦问题。
- PR 描述必须包含目的、关联 OpenSpec change、验证命令和 UI 截图（如适用）。
- 不得删除测试或削弱权限、SSE、工具审计和真实数据边界来通过构建。

## 真实集成

普通 CI 不读取真实云凭据。真实 CLS、MCP、Milvus 与模型验收必须通过文档中的显式本地流程执行，并且不得把凭据或原始用户内容复制到 Issue、PR 或日志中。
