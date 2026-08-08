## ADDED Requirements

### Requirement: 活跃告警只聚合已启用且有效的来源
告警订阅 SHALL 忽略显式关闭的占位来源，并在至少一个启用来源成功时返回该来源的真实结果，包括空集合。

#### Scenario: 外部占位源关闭且本地 Alertmanager 返回空集合
- **WHEN** 外部 Prometheus `enabled=false` 且已启用的本地 Alertmanager 返回有效空数组
- **THEN** 活跃告警 API MUST 返回 HTTP 200 和空 items，前端 MUST 显示当前没有活跃告警

#### Scenario: 一个启用来源运行时失败而另一个成功
- **WHEN** 一个启用来源不可用而另一个启用来源返回有效响应
- **THEN** API MUST 返回成功来源的真实告警结果

#### Scenario: 所有启用来源均不可用
- **WHEN** 每个启用来源都超时、失败或返回无效响应
- **THEN** API MUST 返回不泄露凭据的标准化服务不可用错误
