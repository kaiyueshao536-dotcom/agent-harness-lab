## Why

当前项目已经能记录 Chat 与 AIOps 的统一 Trace，但仍缺少可重复、可量化的质量验证闭环；Prompt、模型、Skill 或工作流变更后，只能依赖人工体验判断是否回退。现在需要把真实执行结果、Trace 指标和确定性规则组织成自动回归评测 Harness，为调优、失败定位和 CI 门禁提供工程依据。

## What Changes

- 新增 owner 范围的评测数据集与版本化案例，案例声明期望文本、禁止文本、必需工具、引用数量、耗时和 Trace 状态等确定性规则。
- 新增 Trace-backed 评测运行：将真实 Chat/AIOps Trace 绑定到案例，由服务端解析对应业务结果与 Trace/Span 指标，批量评分并持久化逐案例检查结果。
- 新增基线对比与质量门禁，计算通过率、平均分、耗时和工具调用变化；门禁不通过时返回明确失败状态。
- 新增离线 CLI，可对提交到仓库的无密钥 fixture 执行相同评分引擎并以退出码支持 CI 回归门禁。
- 新增评测 HTTP/OpenAPI 合同与桌面“自动评测”工作台，支持创建数据集、绑定 Trace 运行、查看失败检查、关联 Trace 和比较基线。
- 更新项目能力矩阵、架构说明和 GitHub Actions，使评测 Harness 可被本地与 CI 复现。

## Capabilities

### New Capabilities

- `agent-evaluation-datasets`: owner 范围的版本化评测数据集、案例和确定性规则定义。
- `agent-evaluation-runs`: Trace-backed 批量评分、逐案例结果、基线对比与质量门禁。
- `agent-evaluation-cli`: 使用同一评分引擎执行无密钥离线 fixture，并通过退出码实施 CI 门禁。
- `agent-evaluation-workspace`: 桌面端数据集、运行、指标、失败检查和 Trace 关联工作台。

### Modified Capabilities

- `api-and-sse-contracts`: 增加评测数据集、运行、详情与基线对比的共享类型和受保护 HTTP/OpenAPI 端点。

## Impact

- 后端新增评测领域模型、SQLite/Alembic 仓库、确定性评分服务、真实 Trace 结果解析、API 与 CLI。
- 共享合同新增评测规则、数据集、运行、逐案例结果和比较类型。
- 前端新增评测客户端、Pinia 状态、路由、导航和桌面主从报告界面。
- CI 新增无模型密钥的离线评测质量门禁；真实 Trace 评测继续使用用户自己的本地 Agent 执行数据。
- 不新增外部 SaaS 或模型依赖，不在评测记录中复制完整提示词、思维链、凭据或原始工具输入。
