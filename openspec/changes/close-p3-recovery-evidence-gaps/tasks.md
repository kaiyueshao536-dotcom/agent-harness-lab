## 1. 执行分组与前端解释

- [x] 1.1 扩展证据链 API，按诊断资源查询独立 Trace 并派生执行分组
- [x] 1.2 扩展共享 TypeScript 合同以描述执行分组和未归属历史记录
- [x] 1.3 更新 AIOps 执行链组件，标明跨执行累计并按 Trace 展示步骤和工具调用
- [x] 1.4 增加 API 与前端组件测试，覆盖两次失败后成功、单次执行和未归属记录

## 2. 报告证据边界与脱敏

- [x] 2.1 从 Report 事实上下文移除历史案例正文，同时保留 Planner 的参考能力
- [x] 2.2 在工具失败或 SearchLog 零结果时使用确定性谨慎报告
- [x] 2.3 修复资源标识占位符的重复右括号问题
- [x] 2.4 增加报告生成和脱敏测试，覆盖历史症状污染、零结果和真实内部标识

## 3. 自动评测闭环

- [x] 3.1 增加 `evidence_cautious` 规则模型和纯评分实现
- [x] 3.2 在评测工作区中公开新规则并保持 API/CLI 合同一致
- [x] 3.3 增加评分、服务和 CLI 测试，覆盖谨慎通过与过度推断失败
- [x] 3.4 编写 P3.2 Dataset 配置说明，组合 `trace_succeeded`、`required_tools`、`evidence_cautious` 和 `excludes_all`

## 4. 验证、复盘与版本

- [x] 4.1 更新 README 版本状态与 P3.2 变更记录
- [x] 4.2 运行 OpenSpec、后端测试、Ruff、Pyright、前端测试与构建
- [x] 4.3 完成人工证据核对并记录无法由 Gate 自动发现的边界
- [x] 4.4 完成 OpenSpec 验证并创建 P3.2 Commit、Tag 后推送 GitHub
