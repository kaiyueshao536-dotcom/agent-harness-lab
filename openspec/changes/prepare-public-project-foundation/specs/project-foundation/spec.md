## ADDED Requirements

### Requirement: Backend assembly has reviewable module boundaries
后端 SHALL 将 API 路由注册、依赖提供、Agent 工作流节点和领域服务保持在职责清晰的模块边界内，同时保留 `super_ai.api.app:create_app` 公共工厂入口。

#### Scenario: Maintainer changes one API domain
- **WHEN** 维护者修改认证、聊天、知识库、MCP、AIOps 或运维端点之一
- **THEN** 对应路由与依赖 MUST 能在领域模块中定位，而无需修改不相关领域的路由实现

#### Scenario: Existing clients use the modularized backend
- **WHEN** 前端和测试继续调用现有 HTTP 路径与 SSE 流
- **THEN** 模块化后的应用 MUST 保持现有路径、响应合同、认证边界和 SSE 事件结构不变

### Requirement: Agent workflow modules remain independently testable
AIOps 工作流 SHALL 将状态、图装配、节点和证据/报告辅助逻辑组织为可单独导入和测试的模块，并且模块导入 MUST NOT 创建外部连接。

#### Scenario: Unit test imports a workflow node
- **WHEN** 测试导入 Planner、Executor、Replanner 或 Reporter 边界
- **THEN** 导入 MUST NOT 连接 SQLite、Milvus、LLM 或 MCP，且节点依赖 MUST 可通过构造函数或显式参数注入
