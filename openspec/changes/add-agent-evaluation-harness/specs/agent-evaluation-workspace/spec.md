## ADDED Requirements

### Requirement: Desktop evaluation workspace
桌面端 SHALL 提供“自动评测”路由和导航入口，使用真实 API 展示数据集、案例、运行历史和质量门禁状态。

#### Scenario: User prepares a trace-backed run
- **WHEN** 用户选择数据集并为每个案例选择匹配执行类型的 Trace
- **THEN** 页面 MUST 提交真实 case/trace 绑定并显示运行结果，不得使用模拟 Agent 输出

#### Scenario: User has no datasets
- **WHEN** 当前 owner 尚未创建数据集
- **THEN** 页面 MUST 显示创建引导与明确空状态，不得展示虚构评测成绩

### Requirement: Evaluation report explains regressions
运行详情 SHALL 展示通过率、平均分、耗时、工具数量、基线变化以及逐案例失败检查，并允许从案例结果跳转到关联 Trace。

#### Scenario: Candidate gate fails
- **WHEN** 用户打开 gate 失败的运行
- **THEN** 页面 MUST 突出失败阈值和未通过规则，并保留对应 Trace 链接

#### Scenario: Candidate has baseline
- **WHEN** 运行引用有效基线
- **THEN** 页面 MUST 显示分数、通过率、耗时和工具调用的变化，且不得把缺失指标展示为改善
