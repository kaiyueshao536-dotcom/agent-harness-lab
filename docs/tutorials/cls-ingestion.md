# 腾讯云 CLS 日志接入：SDK 与 LogListener

本项目支持两条互补的日志接入路径：

| 场景 | 推荐入口 | 说明 |
| --- | --- | --- |
| 安全测试批次、结构化领域事件 | Python CLS SDK | 业务任务显式调用，字段和批次可控 |
| 服务器持续产生的 JSON 文件日志 | LogListener | 无侵入监听文件，适合生产运维 |

同一类日志只能选择一个入口。不要先用 SDK 写入 CLS，又让 LogListener 采集同一事件的落盘副本，否则会产生重复计数。

## 一、公共字段约定

SDK 上传服务会增加以下来源字段：

- `region`：目标 CLS 地域，例如 `ap-guangzhou`
- `environment`：项目环境，例如 `development`、`test` 或 `production`
- `ingestion_method`：固定为 `python-sdk`
- `host`：业务主机或显式来源

业务日志建议至少包含：

```json
{
  "timestamp": "2026-07-30T10:00:00Z",
  "level": "ERROR",
  "service": "order-service",
  "event": "checkout_failed",
  "trace_id": "trace-123",
  "message": "Inventory reservation timed out"
}
```

不得记录 `SecretId`、`SecretKey`、API Key、密码、Authorization、Token、Cookie、完整提示词或真实用户隐私数据。

## 二、业务服务通过 Python SDK 上传

项目的公共入口位于 `super_ai.cls_ingestion`。它只从 merged `config/project.json` 与 `config/user.project.json` 读取配置，不从环境变量读取应用凭据，也不会在模块导入时连接腾讯云。

业务任务示例：

```python
from super_ai.cls_ingestion import create_cls_ingestion_service


def publish_order_events() -> None:
    service = create_cls_ingestion_service()
    result = service.upload(
        [
            {
                "timestamp": "2026-07-30T10:00:00Z",
                "level": "ERROR",
                "service": "order-service",
                "event": "checkout_failed",
                "trace_id": "trace-123",
                "message": "Inventory reservation timed out",
            }
        ],
        filename="order-service-events.jsonl",
        source="order-service-01",
    )
    print(result.request_id)
```

建议从后台任务或消息消费任务调用，不要在 HTTP 请求主链路中同步上传，以免 CLS 网络延迟影响业务响应时间。

测试数据先 dry-run：

```bash
cd apps/backend
uv run python scripts/generate_and_upload_cls_logs.py --profile java-ecommerce --dry-run
```

确认字段后显式上传：

```bash
uv run python scripts/generate_and_upload_cls_logs.py --profile java-ecommerce
```

量化服务测试批次支持有界计数：

```bash
uv run python scripts/generate_and_upload_cls_logs.py --profile quant --count 12
```

## 三、Linux 服务器配置 LogListener

腾讯云建议在目标服务器安装 LogListener、创建机器组、绑定采集配置并开启索引。完整版本与系统支持范围以[腾讯云 Linux LogListener 安装指南](https://cloud.tencent.com/document/product/614/122939)为准。

### 1. 准备最小权限身份

为 LogListener 单独创建 CAM 子账号或角色，只授权目标日志主题所需的采集权限。不要使用主账号密钥，不要把凭据写入仓库。

### 2. 安装 LogListener 3.4.0+

腾讯云服务器且与 CLS 同地域时使用内网：

```bash
wget https://mirrors.tencentyun.com/install/cls/script/loglistener/loglistener_operator
chmod u+x loglistener_operator
sudo ./loglistener_operator install \
  -s "${TENCENT_SECRET_ID}" \
  -k "${TENCENT_SECRET_KEY}" \
  -r ap-guangzhou
```

非腾讯云服务器或跨地域机器使用外网：

```bash
wget https://mirrors.tencent.com/install/cls/script/loglistener/loglistener_operator
chmod u+x loglistener_operator
sudo ./loglistener_operator install \
  -s "${TENCENT_SECRET_ID}" \
  -k "${TENCENT_SECRET_KEY}" \
  -r ap-guangzhou \
  -n internet
```

安装参数中的 region 是 CLS 日志主题所在地域，不是业务服务器地域。

### 3. 创建机器组

1. 打开腾讯云 CLS 控制台。
2. 进入“机器组”，创建 Linux 机器组。
3. 推荐使用机器标识，例如 `super-ai-prod`。
4. 安装 LogListener 时配置相同 label，或按控制台说明使用机器 IP。
5. 确认机器组心跳正常后再创建采集配置。

使用 label 后，该机器只能通过机器标识关联机器组，不能同时通过 IP 关联。

### 4. 配置 JSON 文件采集

业务服务应输出 UTF-8 JSONL，一行一个完整 JSON 对象，例如：

```text
/var/log/super-ai/business-events.jsonl
```

在目标日志主题中：

1. 进入“采集配置”。
2. 单击“新增”。
3. 选择“服务器及应用”→“JSON-文件日志”。
4. 绑定 `super-ai-prod` 机器组。
5. 目录前缀填写 `/var/log/super-ai`。
6. 文件名填写 `business-events*.jsonl`。
7. 选择增量采集，避免首次接入上传全部历史文件。
8. 开启“解析失败上传”，避免格式异常日志被直接丢弃。

JSON 文件路径和解析规则详见[腾讯云 JSON 提取模式](https://cloud.tencent.com/document/product/614/17419)。LogListener 对单行、文件轮转、过滤规则和配置生效时间存在限制，部署前需检查[LogListener 限制说明](https://cloud.tencent.com/document/product/614/63513)。

### 5. 配置索引

至少为以下字段开启键值索引与 SQL 分析：

| 字段 | 类型 |
| --- | --- |
| `timestamp` | text |
| `level` | text |
| `service` | text |
| `event` | text |
| `trace_id` | text |
| `message` | text |
| `host` | text |
| `environment` | text |
| `ingestion_method` | text |

同时可开启全文索引用于 message 关键词检索。索引修改通常只对之后写入的数据生效。

### 6. 验证

```bash
systemctl status loglistener
systemctl check loglistener
```

写入一条新的 JSONL 日志后，在 CLS 检索：

```text
service:order-service AND trace_id:trace-123
```

LogListener 的工作机制与 checkpoint 行为见[腾讯云采集机制说明](https://cloud.tencent.com/document/product/614/17415)。

## 四、Windows Server 配置 LogListener

腾讯云 Windows LogListener 只支持 64 位 Windows Server 2012 R2、2016、2019、2022、2025；文本日志采集要求 LogListener 2.9.7 以上。Windows 10/11 桌面系统不在官方支持范围内，不能把本地开发机当成生产 LogListener 节点。具体支持范围见[Windows LogListener 安装指南](https://cloud.tencent.com/document/product/614/96677)。

以管理员身份运行安装包中的命令：

```powershell
.\loglistener_installer.exe install `
  --secret_id "<专用 CAM SecretId>" `
  --secret_key "<专用 CAM SecretKey>" `
  --region ap-guangzhou `
  --network internet `
  --label super-ai-windows-prod `
  --encryption true
```

然后在 CLS 控制台：

1. 创建系统环境为 Windows 的机器组。
2. 使用 `super-ai-windows-prod` 机器标识关联服务器。
3. 添加“JSON-文件日志”采集配置。
4. 示例目录前缀：`C:\ProgramData\SuperAI\logs`。
5. 示例文件名：`business-events*.jsonl`。
6. 配置与 Linux 相同的键值索引。

检查版本和心跳：

```powershell
Set-Location "C:\Program Files (x86)\Tencent\LogListener"
.\loglistener_work.exe -v
.\loglistener_work.exe check
```

## 五、来源识别和避免重复

- SDK 日志：`ingestion_method=python-sdk`，`FileName` 来自调用参数。
- LogListener 日志：使用机器组自定义元数据，例如 `__TAG__.ingestion_method=loglistener`。
- 一个业务事件只能走一条上传路径。
- 如果业务同时产生领域事件和普通文件日志，应使用不同的 `event`/`log_type` 值或不同日志主题。
- 验收时同时检查 `trace_id`、`service`、`host` 和 ingestion 来源，不要只按 message 计数。
