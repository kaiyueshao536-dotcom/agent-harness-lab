## ADDED Requirements

### Requirement: Secretless offline evaluation CLI
仓库 SHALL 提供使用纯评分内核的离线 CLI，能够读取有界 JSON fixture、输出机器可读报告，并且不连接模型、Milvus、CLS、MCP 或数据库。

#### Scenario: Fixture passes quality gate
- **WHEN** CLI 输入的全部案例观察达到声明门禁
- **THEN** CLI MUST 输出包含聚合指标和逐案例结果的 JSON，并以退出码 0 结束

#### Scenario: Fixture fails quality gate
- **WHEN** 至少一个质量门禁未达到
- **THEN** CLI MUST 输出失败原因并以非零退出码结束

#### Scenario: Fixture is invalid
- **WHEN** fixture 包含未知规则、缺失观察或无效阈值
- **THEN** CLI MUST 安全失败且不得执行 fixture 中的任何代码

### Requirement: CI evaluation gate
持续集成 SHALL 在无业务密钥环境运行一个提交到仓库的确定性回归 fixture，并将 gate 失败视为构建失败。

#### Scenario: Pull request introduces scoring regression
- **WHEN** 提交修改评分行为导致固定 fixture 低于门禁
- **THEN** GitHub Actions MUST 返回失败并阻止该质量门禁静默通过
