## 1. 共享合同与 Trace 基础

- [x] 1.1 在共享 Trace/OpenAPI 合同和前端时间线中增加 `attempt` Span kind
- [x] 1.2 扩展 Trace Service execution context，使已直接埋点的工具 Span 不会被缓冲 SSE 事件重复终结
- [x] 1.3 为 Trace/Span 父子关系、真实耗时和安全 Attempt 属性补充后端测试

## 2. MCP Attempt 与真实工具 Span

- [x] 2.1 为 `LocalMcpClient.call_tool` 增加中立的 Attempt observer 和安全 Attempt 事件模型
- [x] 2.2 在 `_run_connection` 中实现 `retries + 1` 次有界指数退避并覆盖首次失败后成功、全部失败测试
- [x] 2.3 在 AIOps Executor 的真实调用边界创建父工具 Span，并把 MCP Attempt 映射为子 Span
- [x] 2.4 保持 Tool Audit 一次逻辑调用语义，并验证工具数量不会被 Attempt Span 放大

## 3. AIOps 关联重试 API

- [x] 3.1 让诊断创建、列表、详情和证据链响应携带 owner/resource 下最新 Background Job
- [x] 3.2 覆盖 failed/cancelled Job 关联重试、非法状态冲突和跨 owner 隔离 API 测试
- [x] 3.3 验证同一诊断 retry Job 重新进入 running、创建新 Trace 并保留原失败 Job/Trace
- [x] 3.4 更新共享 Background Job/AIOps OpenAPI 合同测试

## 4. AIOps 桌面恢复交互

- [x] 4.1 在 AIOps client/store 中调用通用 Background Job retry API并重新订阅同一诊断 SSE
- [x] 4.2 在失败报告区域展示中文重试按钮、禁用重复提交并保留错误反馈
- [x] 4.3 增加 Pinia store、client 和 Vue 组件测试，覆盖成功恢复与请求拒绝

## 5. Evaluation 失败/恢复验证

- [x] 5.1 让 Evaluation 工作台按执行类型加载成功和失败 Trace，并明确展示状态
- [x] 5.2 让 Case Builder 为同一案例暂存、查看和提交多条确定性规则
- [x] 5.3 增加失败 Trace 负例、多规则评分和恢复 Trace 正例的前端/服务测试
- [x] 5.4 增加无密钥 P3 离线 fixture 或确定性测试，验证 Gate 能区分失败与恢复

## 6. 验证、文档与版本交付

- [x] 6.1 运行 OpenSpec、后端 pytest/Ruff/Pyright、合同 typecheck、前端 test/typecheck/build 和 docs build
- [x] 6.2 使用真实本地 MCP 完成失败注入、关联重试、Attempt Trace 和 Evaluation Gate 验收
- [x] 6.3 更新 README、CHANGELOG、P3 版本复盘与学习文档，明确范围、证据和已知限制
- [x] 6.4 创建独立 Conventional Commit、注释 Tag `p3-trace-driven-tool-failure-recovery` 并推送核对 GitHub
