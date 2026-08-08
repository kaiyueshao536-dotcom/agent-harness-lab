## ADDED Requirements

### Requirement: Dataset-scoped evaluation run draft
自动评测工作台 SHALL 将 Trace 绑定和 Baseline 作为当前 Dataset 的局部运行草稿；创建或切换 Dataset 时 MUST 清除不属于新 Dataset 的草稿状态。

#### Scenario: Create dataset after binding an existing dataset
- **WHEN** 用户已为当前 Dataset 选择 Trace，随后创建一个新 Dataset 版本
- **THEN** 页面 MUST 清除旧 Case 的 Trace 绑定和旧 Baseline，并允许用户为新 Case 重新选择 Trace 后首次运行成功

#### Scenario: Switch between existing datasets
- **WHEN** 用户从一个已有 Dataset 切换到另一个已有 Dataset
- **THEN** 页面 MUST 清除前一个 Dataset 的 Trace 绑定和 Baseline，不得在运行请求中提交前一个 Dataset 的 Case ID

### Requirement: Backend binding validation remains strict
前端状态清理 SHALL NOT 放宽后端对 Dataset Case 与 Trace 绑定集合的精确校验。

#### Scenario: Client submits a foreign case binding
- **WHEN** 客户端提交包含不属于目标 Dataset 的 Case ID
- **THEN** 后端 MUST 拒绝运行请求，且不得创建部分 Evaluation Run
