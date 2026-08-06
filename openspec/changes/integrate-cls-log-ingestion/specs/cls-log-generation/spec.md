## MODIFIED Requirements

### Requirement: Standalone safe CLS log seeding script
仓库 SHALL 提供独立的 Python 脚本，生成安全的结构化 Java 电商服务事件日志，并通过公共 CLS ingestion 服务执行 dry-run 或显式真实上传。脚本 MUST 在受支持的 Windows/Python 3.11 环境中通过锁定依赖安装，不得要求开发者为了旧传递依赖安装 MSVC。

#### Scenario: Script previews a generated batch
- **WHEN** 开发者使用 `--dry-run` 调用脚本
- **THEN** 脚本 MUST 校验并汇总将要上传的记录、字段和来源，且 MUST NOT 创建 CLS 网络请求

#### Scenario: Script uploads a generated batch
- **WHEN** 开发者使用有效配置显式调用上传脚本
- **THEN** 它 MUST 通过公共 ingestion 服务和腾讯云官方 Python CLS SDK 将生成批次上传到 merged 项目配置的主题，并输出不含凭据的上传摘要

#### Scenario: Script reads tracked target configuration
- **WHEN** 脚本运行时
- **THEN** 它 MUST 从 merged 项目配置中读取地域、端点、日志集 ID、主题 ID 和 CLS 凭据，而不读取本地环境变量

#### Scenario: Base config leaves personal CLS target fields empty
- **WHEN** 检查 `config/project.json`
- **THEN** `clsLogUpload.region`、`clsLogUpload.logsetId` 和 `clsLogUpload.topicId` MUST 为空字符串，并由用户配置文件覆盖

#### Scenario: Batch size is bounded
- **WHEN** 提供的计数超出配置范围
- **THEN** 脚本 MUST 在联系 CLS 之前停止

### Requirement: Java e-commerce incident log batch
CLS 辅助脚本 SHALL 从共享场景目录生成并上传 10 条 Java 电商微服务结构化关键日志，并为每条记录增加可查询的 SDK ingestion 来源元数据。

#### Scenario: Ten logs are generated
- **WHEN** 执行 Java 电商日志生成流程
- **THEN** 输出 MUST 恰好包含 10 条不同 incident 和 trace ID 的日志，并包含 service、alertname、sop、异常类型、耗时或资源指标

#### Scenario: Logs remain safe
- **WHEN** 日志批次被上传到 CLS
- **THEN** 任何日志 MUST NOT 包含 API key、SecretId、SecretKey、密码、token 或真实用户数据

#### Scenario: Uploaded logs are traceable
- **WHEN** 通过 SearchLog 查询已上传的 fixture
- **THEN** 每条结果 MUST 可以通过 fixture、trace_id、service、host 和 ingestion_method 识别其测试来源

## ADDED Requirements

### Requirement: Modern compression dependency resolution
后端锁定依赖 SHALL 为官方 CLS SDK 解析无需本地 C++ 编译的兼容 `python-snappy` 和 `lz4` 版本。

#### Scenario: Windows developer synchronizes dependencies
- **WHEN** Windows/Python 3.11 开发者执行 `uv sync`
- **THEN** 依赖安装 MUST 使用可用 wheel 完成，且 MUST NOT 因 `python-snappy==0.6.0` 或 `lz4==3.1.2` 请求 MSVC
