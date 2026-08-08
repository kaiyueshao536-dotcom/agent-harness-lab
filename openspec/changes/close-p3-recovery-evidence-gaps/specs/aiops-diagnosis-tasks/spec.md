## ADDED Requirements

### Requirement: 当前执行事实与历史计划参考隔离
Report 节点 SHALL 只把当前诊断 Query、当前告警输入和本次执行工具结果作为当前事实证据；SOP 与历史案例 SHALL 仅作为 Planner 的计划参考，MUST NOT 将其正文中的症状、日志或根因写成本次事实。

#### Scenario: 历史案例包含无关症状
- **WHEN** Planner 检索到包含“结算服务 API 延迟升高”的历史案例，但当前输入只要求验证 learning-demo 的 CLS 查询且本次工具没有该症状证据
- **THEN** 最终报告 MUST NOT 把“结算服务 API 延迟升高”写入当前症状、关键发现或根因结论

#### Scenario: 当前工具证据与历史案例一致
- **WHEN** 当前工具结果独立返回与历史案例相同的症状证据
- **THEN** 报告 MAY 基于当前工具结果陈述该症状，并 MUST 将当前工具调用作为来源

### Requirement: 零结果报告保持不确定性
当 SearchLog 成功但返回零条可解析记录时，Report 节点 SHALL 生成确定性谨慎报告，只说明当前查询没有匹配日志，并 MUST NOT 将其直接解释为 Topic 无数据或采集链路异常。

#### Scenario: SearchLog 返回 recordCount 零
- **WHEN** 本次 SearchLog 状态为 completed 且结果为 `recordCount=0`
- **THEN** 报告 MUST 说明“当前查询未匹配到可解析日志”和“证据不足，无法确认原因”，并 MUST NOT 断言采集链路异常

#### Scenario: SearchLog 工具失败
- **WHEN** 本次 SearchLog 在有限 Attempt 后失败
- **THEN** 报告 MUST 如实说明外部工具不可用和需要恢复后重试，并 MUST NOT 使用历史成功或失败结果代替本次执行证据
