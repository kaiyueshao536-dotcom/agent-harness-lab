## ADDED Requirements

### Requirement: Explicit CLS structured log ingestion service
系统 SHALL 提供可复用的 CLS 结构化日志上传服务，调用方 MUST 在显式初始化或任务执行路径中使用 merged 项目配置创建该服务，模块导入期间 MUST NOT 读取凭据、创建客户端或访问网络。

#### Scenario: Business task uploads structured events
- **WHEN** 业务任务使用有效配置和安全的结构化事件显式调用上传服务
- **THEN** 服务 MUST 使用腾讯云官方 Python CLS SDK 将单个有界批次写入配置的地域和日志主题

#### Scenario: Module is imported
- **WHEN** 应用或测试导入 CLS ingestion 模块
- **THEN** 系统 MUST NOT 连接腾讯云、读取本机环境变量或创建外部客户端

### Requirement: Safe bounded CLS batches
上传服务 MUST 校验批次大小、字段数量、字段名称和值，并 MUST 阻止包含凭据、密码、Token 或其他敏感键名的记录发送到 CLS。

#### Scenario: Safe batch is prepared
- **WHEN** 调用方提交满足边界的结构化记录
- **THEN** 服务 MUST 构建 CLS LogGroup，并补充可查询的 region、host、environment 和 ingestion_method 来源字段

#### Scenario: Sensitive field is present
- **WHEN** 任一记录包含 SecretId、SecretKey、password、authorization 或 token 等敏感键
- **THEN** 服务 MUST 在创建网络请求前拒绝整个批次

#### Scenario: Batch exceeds configured maximum
- **WHEN** 批次数量超过 merged 配置的上限
- **THEN** 服务 MUST 在创建网络请求前返回可操作的校验错误

### Requirement: LogListener production collection path
仓库 SHALL 记录腾讯云 LogListener 的生产文件采集路径，包括受支持系统、安装、机器组关联、JSON 文件采集、索引配置、心跳检查和端到端查询验证。

#### Scenario: Linux operator configures collection
- **WHEN** 运维人员在受支持的 Linux 服务器部署 LogListener
- **THEN** 指南 MUST 要求使用目标 CLS 地域、最小权限凭据、机器标识和一行一条 JSON 的 UTF-8 文件路径完成配置

#### Scenario: Windows operator configures collection
- **WHEN** 运维人员在 Windows 上评估 LogListener
- **THEN** 指南 MUST 明确文本日志采集仅支持官方列出的 64 位 Windows Server，并给出版本、安装和检查命令

#### Scenario: SDK and LogListener coexist
- **WHEN** 同一环境同时使用业务 SDK 和 LogListener
- **THEN** 指南 MUST 要求每类日志只选择一个入口，并通过来源元数据避免重复计数
