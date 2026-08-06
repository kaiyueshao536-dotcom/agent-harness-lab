## Context

项目已经具备真实 CLS MCP 查询能力、merged 本地配置和安全的合成 AIOps 日志生成器，但上传脚本直接构建 SDK 客户端，无法被业务模块复用。`tencentcloud-cls-sdk-python==1.0.4` 还固定依赖只发布源码包的旧 `python-snappy`/`lz4` 版本，在 Windows/Python 3.11 上触发本地 C++ 编译并失败。当前 CLS 主题因此可访问但没有日志。

LogListener 与 SDK 解决不同问题：LogListener 适合服务器文件日志的无侵入持续采集；SDK 适合业务服务显式上报结构化领域事件和生成受控测试数据。两者必须共享同一主题字段约定，但不能对同一日志文件重复采集。

## Goals / Non-Goals

**Goals:**

- 在受支持的 Windows、Linux 和 macOS Python 环境中安装并运行 CLS 上传依赖。
- 提供显式创建、可注入客户端、无模块导入网络副作用的 CLS 上传边界。
- 对上传批次进行边界校验、来源标记和敏感字段拒绝/脱敏。
- 让测试脚本支持 dry-run，并复用公共上传边界完成真实上传。
- 提供 Linux/Windows Server LogListener、机器组、JSON 文件采集、索引和验收说明。
- 用真实云端 SearchLog 结果证明上传成功及来源可追踪。

**Non-Goals:**

- 不在开发者 Windows 桌面系统自动安装 LogListener；腾讯云 Windows LogListener 仅支持 Windows Server。
- 不自动创建或删除腾讯云日志集、主题、机器组和采集配置。
- 不默认将每个 HTTP 请求同步上传到 CLS，避免外部网络抖动影响请求延迟。
- 不采集历史本地文件、模型提示词、凭据、Token 或真实用户内容。

## Decisions

### 保留官方 Python CLS SDK并覆盖不兼容的传递依赖

继续固定 `tencentcloud-cls-sdk-python==1.0.4`，在 uv 的 override 中将 `python-snappy` 与 `lz4` 提升到提供现代 Python wheel 且保持 API 兼容的版本。这样保留官方上传协议实现，又不要求开发者安装完整 MSVC 工具链。

备选方案是改用通用云 API 或在 Python 中自行签名、编码 protobuf；这会复制官方 SDK 逻辑，增加签名和压缩兼容风险，因此不采用。

### 将上传构建放入可注入的服务边界

新增 `super_ai.cls_ingestion`，包含不可变配置、批次校验、LogGroup 构建和上传服务。模块导入时不读取配置、不创建客户端、不访问网络；调用者在显式初始化路径中加载 merged 配置并创建服务。客户端协议可注入，以便测试不访问腾讯云。

测试日志脚本只负责选择 fixture、处理 CLI 参数和展示结果，SDK 细节统一交给服务。

### 上传结构保持扁平字符串字段与明确 provenance

每条记录转换为 CLS key-value 字段，并补充 `region`、`host`、`ingestion_method=python-sdk` 与 `environment` 等来源字段。字段名、单条记录数和批次大小受限；敏感键名匹配凭据、密码、Token 等模式时拒绝上传，而不是静默发送。

### LogListener 作为生产文件采集路径

文档要求业务进程输出一行一个 JSON 对象的 UTF-8 JSONL 文件，由 LogListener 的“JSON-文件日志”采集配置绑定机器组和目标主题。Linux 服务器优先使用 LogListener 3.4.0+；Windows 仅覆盖官方支持的 64 位 Windows Server 和 2.9.7+ 文本采集版本。

同一类事件在一个环境中只能选择 SDK 或 LogListener 之一，防止重复日志。SDK 用于结构化领域事件和测试；LogListener 用于持续采集应用文件。

### 真实云端验收保持显式

测试默认先执行 dry-run；只有显式运行上传命令才写入 CLS。验收在上传后使用 `SearchLog` 查询 fixture/trace 字段，并记录返回数量、文件名、来源地址和 `ingestion_method`，不输出凭据。

## Risks / Trade-offs

- [上游 SDK 未声明支持新版压缩库] → 通过锁文件、Windows 安装验证、单元测试和真实上传验证兼容性。
- [同步 SDK 上传可能阻塞业务请求] → 公共服务作为显式批次边界，不自动挂入请求中间件；生产调用方应从后台任务或队列调用。
- [LogListener 和 SDK 重复采集] → 文档明确每类日志选择单一入口，并用 `ingestion_method`/机器组元数据区分来源。
- [本地凭据泄露] → 继续只从被忽略的 merged 配置读取，测试与日志禁止输出 SecretId/SecretKey。
- [目标服务器信息缺失] → 仓库提供可执行指南和字段约定；实际机器组绑定必须在已知目标主机 IP 或 label 后由运维执行。

## Migration Plan

1. 更新依赖覆盖并重新生成 `uv.lock`，确认 `uv sync` 无需本地 C++ 编译。
2. 增加公共 CLS 上传服务及单元测试。
3. 重构 fixture 上传脚本，先执行 dry-run。
4. 更新 LogListener/SDK 文档和配置模板说明。
5. 使用用户已配置的测试主题显式上传安全 fixture。
6. 通过 CLS SearchLog 验证日志与来源。

回滚时可恢复依赖声明和旧脚本；公共服务和文档可直接移除。已上传的测试日志带有 `fixture` 与 `ingestion_method` 标记，可按主题保留周期自然过期，或由用户在腾讯云控制台按治理策略处理。

## Open Questions

- 生产环境目标服务器的操作系统、IP/机器标识和实际日志目录尚未提供，因此本变更不自动创建机器组或安装 LogListener。
- 生产业务事件是否进入消息队列后异步上传，需要结合最终部署拓扑另行设计。
