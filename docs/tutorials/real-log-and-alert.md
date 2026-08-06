# 真实 CLS 日志、告警与 SOP 教程

本教程生成 10 套 Java 电商微服务故障。每套数据均包含唯一 trace ID、一条 CLS 关键日志、一条 Alertmanager 活动告警和一份处理 SOP，并通过一致的 `incident_id`、`service`、`alertname` 与 `sop` 字段关联。

完整场景及根因说明见 [Java 电商微服务 AIOps 测试数据](../aiops/ecommerce-aiops-fixture.md)。

## 前置条件

1. 按操作系统安装指南完成依赖安装。
2. 在仓库根目录执行 `./scripts/start-local.sh` 或 Windows 的 `scripts\start-local.bat`。
3. 确认 `http://127.0.0.1:8000/ready` 返回就绪状态。
4. 检查项目配置中的 `clsLogUpload`、`clsMcpServer`、`prometheusAlerts` 和 `aiopsDemo` 指向目标测试环境。

## 1. 上传 10 条真实 CLS 日志

在 `apps/backend` 先执行不联网的 dry-run：

```bash
uv run python scripts/generate_and_upload_cls_logs.py --profile java-ecommerce --dry-run
```

确认输出中 `count=10`，字段包含 `fixture`、`trace_id`、`service`、`host` 和 `ingestion_method`，再显式上传：

```bash
uv run python scripts/generate_and_upload_cls_logs.py --profile java-ecommerce
```

脚本通过项目公共 ingestion 服务和腾讯云官方 CLS SDK 上传 10 条结构化 Java 日志。每条日志属于不同微服务和 incident，包含唯一 trace ID、异常类、依赖组件、指标观测值、触发阈值、匹配 SOP 和 `ingestion_method=python-sdk`，不包含密钥、Token 或客户数据。

上传后等待短暂索引延迟，在对话页面执行：

```text
请实际调用腾讯 CLS MCP 的 SearchLog，查询 ap-guangzhou 中已配置 TopicId 最近15分钟的日志。
Query = fixture:java-ecommerce AND ingestion_method:python-sdk
Sort = desc
Limit = 20
返回 trace_id、service、host、FileName 和日志数量，不得编造结果。
```

持续生产日志采集与业务 SDK 接入见[腾讯云 CLS 日志接入：SDK 与 LogListener](cls-ingestion.md)。

## 2. 发布 10 条本地活动告警

启动器已启动 Alertmanager。执行：

```bash
uv run python scripts/publish_java_ecommerce_alerts.py --profile java-ecommerce
```

脚本通过 Alertmanager v2 API 一次发布 10 条告警。所有告警均标记为 `environment=test`、`fixture=java-ecommerce`，可在 `http://127.0.0.1:9093` 查看。

## 3. 上传并索引 10 份关联 SOP

```bash
uv run python scripts/seed_java_ecommerce_aiops_sops.py --profile java-ecommerce
```

脚本使用 `aiopsDemo` 账户通过真实后端 API 上传 10 份 Markdown SOP，并逐份等待 Milvus 索引成功。每份 SOP 包含对应 trace 查询、指标阈值、根因假设、排查步骤、恢复动作和验证标准。

## 4. 从前端执行诊断

1. 打开 `http://127.0.0.1:5173` 并登录。
2. 进入 **AIOps diagnosis** 页面并刷新活动告警。
3. 选择任一 `java-ecommerce` 告警并开始诊断。
4. 等待 Planner、Executor、Replanner、Report 的 SSE 事件结束。

成功证据链必须包括选中告警、同 incident 的 SOP 知识引用，以及通过真实 CLS MCP `SearchLog` 查询到的相同 trace ID 日志。某个工具失败时报告必须如实说明，不得使用其他场景证据填充。

## 常见排查

- Milvus 未就绪：确认 `etcd`、`minio` 和 `milvus` 容器健康。
- MCP 失败：确认 `cls-mcp-server` 本机进程监听 `3000` 端口。
- 上传依赖失败：重新执行 `uv sync`，锁文件应解析 `python-snappy 0.7.3` 和 `lz4 4.4.5`，不再要求 MSVC。
- CLS 查询无新日志：核对地域、主题 ID 与凭据，等待短暂写入延迟后按 trace ID 重试。
- SearchLog 返回字段不可检索：在 CLS 主题的索引配置中为 `fixture`、`trace_id`、`service`、`host` 和 `ingestion_method` 开启键值索引。
- 没有活动告警：再次运行 `publish_java_ecommerce_alerts.py --profile java-ecommerce`。
- SOP 未命中：确认 10 个索引任务均为 `succeeded`，并使用告警 annotations 中的 SOP ID 检索。
