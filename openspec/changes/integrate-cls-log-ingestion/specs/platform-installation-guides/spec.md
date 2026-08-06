## MODIFIED Requirements

### Requirement: Real log and alert upload tutorial
仓库 SHALL 提供中文教程，区分普通启动、业务 SDK 显式上传、LogListener 持续文件采集、本地 Alertmanager 告警发布、SOP 索引以及告警驱动的 AIOps 诊断。

#### Scenario: Developer follows the SDK operations tutorial
- **WHEN** 开发人员需要一个真实的 Java 电商事件演示
- **THEN** 教程 MUST 提供 dry-run、CLS 上传、SearchLog 验证、Alertmanager 告警和 SOP 索引的准确命令，并描述预期的 AIOps 证据链

#### Scenario: Operator follows the LogListener tutorial
- **WHEN** 运维人员需要持续采集服务器 JSON 文件日志
- **THEN** 教程 MUST 提供官方安装文档、受支持系统、机器组关联、采集路径、JSON 解析、索引、心跳和检索验证步骤

## ADDED Requirements

### Requirement: CLS ingestion mode selection guide
仓库 SHALL 说明 SDK 与 LogListener 的适用场景、安全边界和避免重复采集的选择规则。

#### Scenario: Team selects an ingestion mode
- **WHEN** 团队评估结构化领域事件或持续文件日志的接入方式
- **THEN** 指南 MUST 推荐领域事件和测试批次使用 SDK、服务器文件日志使用 LogListener，并禁止同一日志同时通过两条路径上传
