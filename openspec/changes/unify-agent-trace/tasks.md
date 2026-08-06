## 1. Trace 数据与服务底座

- [x] 1.1 新增 Agent Trace/Span SQLAlchemy 模型、Alembic 迁移和 owner/时间查询索引
- [x] 1.2 新增 Trace/Span 记录类型、仓库协议和 SQLite 实现，覆盖创建、终结、列表与详情查询
- [x] 1.3 新增 `AgentTraceService`，统一 ID、状态、sequence、安全摘要和降级日志行为
- [x] 1.4 增加迁移、仓库、权限隔离、顺序和敏感字段测试

## 2. 聊天与 AIOps 执行接入

- [x] 2.1 在流式聊天入口创建/终结 Trace，并为工具生命周期创建和终结 Span
- [x] 2.2 让聊天所有 SSE 事件共享 `traceId`，工具事件携带 `spanId`
- [x] 2.3 在 AIOps 后台执行入口创建/终结 Trace，并将图阶段与工具事件映射为有序 Span
- [x] 2.4 让 AIOps SSE 与结构化完成/失败日志携带同一 `traceId`
- [x] 2.5 增加聊天、AIOps 成功/失败、工具 Span 复用和 Trace 写入降级测试

## 3. 共享合同与查询 API

- [x] 3.1 在 `packages/api-contracts` 新增 Trace/Span 类型、SSE Trace 上下文与导出
- [x] 3.2 在 OpenAPI 新增 `GET /agent-traces` 与 `GET /agent-traces/{traceId}` 及 schema
- [x] 3.3 新增后端 owner 范围 Trace 列表/详情 API、筛选、序列化与 404 边界
- [x] 3.4 增加合同类型检查、OpenAPI、API 筛选和跨用户访问测试

## 4. 桌面端执行追踪

- [x] 4.1 新增 Trace 客户端与状态加载边界，支持列表筛选、选择和刷新详情
- [x] 4.2 新增“执行追踪”路由与桌面导航入口
- [x] 4.3 实现 Trace 列表、指标摘要和有序 Span 时间线视图，不展示模拟记录
- [x] 4.4 增加路由、客户端、空状态、筛选和 Trace 详情渲染测试

## 5. 验证与文档

- [x] 5.1 更新 README 能力矩阵和架构文档，说明 Trace 数据边界与演示路径
- [x] 5.2 运行 OpenSpec、共享合同、后端 Ruff/Pyright/Pytest 和前端类型检查/测试/构建
- [x] 5.3 复核 Trace/API/SSE 不包含模型密钥、完整提示词、思维链或原始工具凭据
