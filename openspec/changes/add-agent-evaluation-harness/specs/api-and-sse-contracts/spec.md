## ADDED Requirements

### Requirement: Shared evaluation HTTP contracts
共享 API-contract 包 SHALL 定义评测规则、数据集、案例、运行、逐案例结果、质量门禁和基线比较类型，并在 OpenAPI 中声明受保护的评测端点。

#### Scenario: Contract exposes dataset APIs
- **WHEN** 客户端检查共享合同
- **THEN** 它 MUST 找到数据集创建、列表和详情端点及其 schema

#### Scenario: Contract exposes run APIs
- **WHEN** 客户端检查共享合同
- **THEN** 它 MUST 找到运行创建、列表和详情端点，并能表达 case/trace 绑定、gate 和 baseline delta

### Requirement: Evaluation endpoints use unified auth and errors
所有评测端点 SHALL 使用 Bearer 身份验证、统一成功/错误信封和 owner 范围资源隐藏语义。

#### Scenario: Anonymous evaluation request
- **WHEN** 未登录客户端访问任一评测端点
- **THEN** API MUST 返回统一 `AUTH_UNAUTHENTICATED` 错误
