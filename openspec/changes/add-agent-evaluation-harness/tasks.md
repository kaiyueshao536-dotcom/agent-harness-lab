## 1. 评测数据与仓储底座

- [x] 1.1 新增数据集、案例、运行和逐案例结果 SQLAlchemy 模型及 owner/版本/时间索引
- [x] 1.2 新增 Alembic 迁移，并验证升级、降级与表结构
- [x] 1.3 新增评测记录类型、仓储协议和 SQLite 实现，覆盖创建、列表、详情与 owner 隔离
- [x] 1.4 增加数据集不可变、名称版本冲突、结果顺序和跨用户仓储测试

## 2. 确定性评分与 Trace-backed 运行

- [x] 2.1 新增封闭规则模型、`EvaluationObservation` 和无外部依赖的纯评分内核
- [x] 2.2 实现文本、工具、引用、耗时、工具数量和 Trace 状态规则及安全说明
- [x] 2.3 实现 Chat/AIOps owner 范围 Trace 观察解析器，不复制完整业务正文
- [x] 2.4 实现批量运行服务、聚合指标、质量门禁和同数据集基线对比
- [x] 2.5 增加成功/失败评分、类型不匹配、跨用户、敏感摘要和基线回退测试

## 3. 共享合同与评测 API

- [x] 3.1 在 `packages/api-contracts` 新增规则、数据集、运行、结果、gate 和 baseline delta 类型
- [x] 3.2 在 OpenAPI 新增评测数据集与运行的创建、列表和详情端点及 schema
- [x] 3.3 新增 Pydantic 请求模型和 owner 范围 FastAPI 路由，统一验证、冲突和 404 语义
- [x] 3.4 增加合同类型、OpenAPI、API 完整运行和权限边界测试

## 4. 桌面端自动评测工作台

- [x] 4.1 新增评测客户端与 Pinia 状态，支持数据集创建、选择、Trace 绑定、运行和详情刷新
- [x] 4.2 新增“自动评测”桌面路由和导航入口
- [x] 4.3 实现数据集创建表单、案例规则摘要、Trace 选择和真实运行提交
- [x] 4.4 实现 gate 指标、基线变化、逐案例失败检查和 Trace 跳转报告
- [x] 4.5 增加客户端、状态、路由、空状态、运行提交和报告渲染测试

## 5. 离线 CLI、CI 与文档

- [x] 5.1 新增离线评测 CLI、严格 JSON fixture 校验、JSON 报告和 gate 退出码
- [x] 5.2 新增无密钥通过/失败 fixture 与 CLI 测试，并将通过 fixture 接入 GitHub Actions
- [x] 5.3 更新 README、架构与评测使用指南，说明 Trace-backed 边界、演示流程和后续 Judge/live runner 路线
- [x] 5.4 运行 OpenSpec、后端 Ruff/Pyright/Pytest、共享合同和前端类型检查/测试/构建
- [x] 5.5 复核评测表、API、CLI 和 UI 不复制完整提示词、思维链、凭据或原始工具输入输出
