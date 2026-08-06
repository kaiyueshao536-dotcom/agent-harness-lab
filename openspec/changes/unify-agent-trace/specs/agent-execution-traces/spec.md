## ADDED Requirements

### Requirement: Unified Agent trace lifecycle
系统 SHALL 为每次有效的聊天或 AIOps Agent 执行创建一个 owner 范围的统一 Trace，并记录执行类型、关联资源、开始时间、终态、结束时间和耗时。

#### Scenario: Successful execution is finalized
- **WHEN** 一次聊天或 AIOps Agent 执行正常完成
- **THEN** Trace MUST 从 `running` 变为 `succeeded`，并包含非负耗时和关联资源 ID

#### Scenario: Failed execution is finalized
- **WHEN** Agent 执行在产生最终结果前失败
- **THEN** Trace MUST 变为 `failed`，记录安全错误类别，并且不得保持为永久 `running`

### Requirement: Ordered execution spans
系统 SHALL 在统一 Trace 下持久化有序 Span，以表示 Agent 阶段、检索、模型、报告和工具调用生命周期，并支持可选父 Span 关系。

#### Scenario: Tool lifecycle maps to one span
- **WHEN** 同一工具调用依次发出 started 和 completed 或 failed 生命周期
- **THEN** 系统 MUST 终结同一个工具 Span，而不是创建两个互不关联的 Span

#### Scenario: Trace detail preserves execution order
- **WHEN** 用户读取 Trace 详情
- **THEN** Span MUST 按稳定 sequence 返回，并包含名称、类型、状态、时间、耗时和可选父 Span ID

### Requirement: Safe trace attributes
系统 SHALL 只持久化服务端白名单 Trace/Span 属性和长度受限的安全摘要，MUST NOT 保存完整提示词、思维链、模型正文、工具凭据或未经裁剪的工具输入输出。

#### Scenario: Secret-bearing tool failure is traced
- **WHEN** 工具失败信息或参数包含 API Key、token、secret 或密码字段
- **THEN** Trace/Span 返回内容 MUST 不包含秘密值，并仅保留工具名、错误类别和安全摘要

### Requirement: Owner-scoped trace query
系统 SHALL 提供经过身份验证的 Trace 列表和详情查询，并在仓库层按当前 owner 过滤。

#### Scenario: User lists own traces
- **WHEN** 已登录用户按执行类型、状态或关联资源筛选 Trace
- **THEN** API MUST 只返回该用户的匹配记录，并按最近开始时间排序

#### Scenario: Cross-owner detail is hidden
- **WHEN** 用户请求另一个 owner 的 `traceId`
- **THEN** API MUST 返回 404，且不得泄露该 Trace 是否存在

### Requirement: Trace execution workspace
桌面端 SHALL 提供“执行追踪”页面，显示 Trace 列表、筛选条件、执行摘要和有序 Span 链路。

#### Scenario: User inspects a trace
- **WHEN** 用户选择一条 Trace
- **THEN** 页面 MUST 显示状态、执行类型、关联资源、总耗时、Span 数量、工具数量以及阶段时间线

#### Scenario: Empty trace history
- **WHEN** 当前用户尚无 Trace
- **THEN** 页面 MUST 显示明确空状态且不得展示模拟执行记录
