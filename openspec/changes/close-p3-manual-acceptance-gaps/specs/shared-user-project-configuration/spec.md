## ADDED Requirements

### Requirement: 告警来源支持显式启停
`prometheusAlerts.sources` 中的每个来源 SHALL 支持布尔 `enabled` 字段；配置加载器 MUST 在校验连接字段前排除禁用来源，并 MUST 至少保留一个有效启用来源。

#### Scenario: 禁用来源缺少连接地址
- **WHEN** 一个来源设置 `enabled=false` 且 `alertsApi` 为空
- **THEN** 配置加载 MUST 忽略该来源且 MUST NOT 因其缺少地址而失败

#### Scenario: 旧来源没有 enabled 字段
- **WHEN** 既有来源没有声明 `enabled`
- **THEN** 系统 MUST 为兼容性将其视为启用并按现有规则校验

#### Scenario: 没有有效启用来源
- **WHEN** 所有来源均禁用或所有启用来源配置无效
- **THEN** 系统 MUST 返回明确的告警 Provider 配置错误
