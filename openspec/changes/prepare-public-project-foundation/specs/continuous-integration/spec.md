## ADDED Requirements

### Requirement: Pull requests execute reproducible quality gates
公共仓库 SHALL 通过 GitHub Actions 在 push 和 pull request 上运行 OpenSpec、后端和前端质量门禁，并在任何必需检查失败时返回失败状态。

#### Scenario: Contributor opens a pull request
- **WHEN** pull request 修改应用代码、规格、测试或工程配置
- **THEN** CI MUST 运行 `openspec validate --all`、后端 Ruff/Pyright/Pytest 以及前端类型检查/测试/构建

### Requirement: Ordinary CI runs without production credentials
普通 CI SHALL NOT 依赖或输出真实模型密钥、CLS 凭据、私有服务地址或用户数据。

#### Scenario: Forked pull request executes CI
- **WHEN** 不受信任 fork 触发普通质量门禁
- **THEN** 所有必需检查 MUST 在没有仓库 Secrets 的情况下完成，并且 MUST NOT 访问真实 CLS、LLM 或私有 MCP 服务

### Requirement: CI uses locked dependency inputs
CI SHALL 使用已提交的 Python 与 Node 锁文件安装依赖，以保持本地和远端验证可复现。

#### Scenario: CI installs dependencies
- **WHEN** GitHub runner 准备后端与前端依赖
- **THEN** Python 安装 MUST 遵守 `uv.lock`，Node 安装 MUST 遵守 `package-lock.json`
