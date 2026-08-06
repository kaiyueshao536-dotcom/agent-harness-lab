## Why

当前项目虽然能够通过 MCP 查询腾讯云 CLS，也提供了测试日志上传脚本，但锁定的旧压缩依赖在 Windows/Python 3.11 上无法安装，实际日志主题仍为空。项目还缺少可复用的业务日志 SDK 边界以及 LogListener 的生产采集说明，导致“能查询”与“有真实日志可查”之间存在断层。

## What Changes

- 新增可复用的腾讯云 CLS 结构化日志上传服务，统一从 merged 项目配置读取目标与凭据，对批次、字段和敏感信息进行校验。
- 修复 Python CLS SDK 在受支持 Python/Windows 环境中的压缩依赖解析，使锁定依赖可以安装并运行。
- 重构测试日志脚本以复用上传服务，并提供 dry-run、明确的上传结果和可查询的来源元数据。
- 补充业务服务通过 SDK 主动上报的接入方式，以及 Linux/Windows Server LogListener、机器组、JSON 文件采集、索引和验证步骤。
- 通过真实 CLS 主题上传安全的合成日志，再使用只读检索验证日志数量、时间、来源与 fixture 标记。

## Capabilities

### New Capabilities

- `cls-log-ingestion`: 定义业务服务通过官方 CLS SDK 上传安全结构化日志，以及运维主机通过 LogListener 采集 JSON 文件日志的行为边界。

### Modified Capabilities

- `cls-log-generation`: 测试日志脚本改为复用公共上传服务，并在 Windows/Python 3.11 环境可安装、可 dry-run、可真实上传验证。
- `platform-installation-guides`: 安装与运维文档增加 LogListener、业务 SDK、索引配置和端到端验证流程。

## Impact

- 后端依赖：`apps/backend/pyproject.toml` 与 `apps/backend/uv.lock`。
- 后端代码：新增 CLS 上传服务，调整 `apps/backend/scripts/generate_and_upload_cls_logs.py`。
- 测试：新增配置、脱敏、批次构建和脚本行为测试。
- 运维与文档：新增 LogListener/SDK 接入指南，更新真实日志与告警教程和配置模板说明。
- 外部系统：腾讯云 CLS 日志主题会在显式验收步骤中写入安全合成测试日志；不会自动上传本地历史文件、凭据或真实用户数据。
