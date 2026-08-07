## ADDED Requirements

### Requirement: Owner-scoped versioned evaluation datasets
系统 SHALL 允许已登录用户创建和读取 owner 范围的版本化评测数据集，数据集名称与版本组合在 owner 范围唯一，并在创建后保持不可变。

#### Scenario: User creates a dataset version
- **WHEN** 用户提交合法名称、版本、质量门禁和至少一个案例
- **THEN** 系统 MUST 持久化数据集及有序案例，并返回稳定数据集 ID

#### Scenario: Duplicate dataset version
- **WHEN** 同一 owner 再次创建相同名称和版本的数据集
- **THEN** 系统 MUST 返回业务冲突且不得覆盖原数据集

#### Scenario: Cross-owner dataset is hidden
- **WHEN** 用户读取另一个 owner 的数据集 ID
- **THEN** 系统 MUST 返回 404 且不得泄露其是否存在

### Requirement: Deterministic evaluation rule catalog
每个案例 SHALL 声明执行类型以及一组经过类型校验的确定性规则，系统 MUST 只接受受支持的规则类型和有界参数。

#### Scenario: Supported regression rules
- **WHEN** 案例使用文本包含/排除、必需工具、最小引用、最大耗时、最大工具数或 Trace 成功规则
- **THEN** 系统 MUST 接受规则并保持其顺序、权重和可读说明

#### Scenario: Executable expression is rejected
- **WHEN** 客户端提交未知规则、脚本、SQL 或超出限制的规则参数
- **THEN** 系统 MUST 返回统一验证错误且不得执行用户提供的代码

### Requirement: Dataset detail is evaluation-ready
数据集详情 SHALL 返回案例、规则和门禁配置，使客户端不依赖本地模拟数据即可准备一次评测运行。

#### Scenario: Empty history with persisted dataset
- **WHEN** 数据集尚未产生任何运行
- **THEN** 详情 MUST 仍完整返回案例和规则，运行历史为空
