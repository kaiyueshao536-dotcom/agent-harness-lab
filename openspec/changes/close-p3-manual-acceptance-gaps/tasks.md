## 1. Trace 可观测界面

- [x] 1.1 根据 `parentSpanId` 计算 Span 展示深度，并对孤儿/循环父链安全回退
- [x] 1.2 为 Tool/Attempt 展示父子连接、Attempt N/M、attemptCount 与安全错误类别
- [x] 1.3 增加 Trace 时间线层级、白名单属性和异常父链组件测试

## 2. 失败诊断恢复入口

- [x] 2.1 重构报告面板，使失败状态、降级报告和重试操作可以同时展示
- [x] 2.2 增加“失败且有报告”“失败且无报告”“成功报告”组件回归测试

## 3. MCP 失败内容脱敏

- [x] 3.1 在 AIOps 面向模型/用户的失败摘要边界移除 MCP URL、CLS Topic ID 与敏感连接字段
- [x] 3.2 保持 Tool Audit 受控原始记录，并增加报告脱敏与审计保留测试

## 4. 活跃告警配置容错

- [x] 4.1 为告警源解析增加兼容的 `enabled` 过滤，只校验启用来源
- [x] 4.2 更新项目配置模板与本地配置，使占位 Prometheus 关闭、本地 Alertmanager 启用
- [x] 4.3 增加禁用空占位源、启用空集合和无有效来源测试

## 5. 验证与记录

- [x] 5.1 运行 OpenSpec、后端 pytest/Ruff/Pyright、前端 test/typecheck/build 和合同检查
- [x] 5.2 在真实浏览器复测 Trace 层级、Attempt 元数据、失败报告重试入口和活跃告警空状态
- [x] 5.3 更新 README、CHANGELOG、P3.1 版本复盘与学习记录
- [x] 5.4 创建独立 Conventional Commit、注释 Tag `p3.1-manual-acceptance-gap-closure` 并推送核对 GitHub
