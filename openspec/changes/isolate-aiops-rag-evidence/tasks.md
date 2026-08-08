## 1. 文档检索元数据

- [x] 1.1 为知识文档上传增加受控 retrieval metadata 表单解析与安全验证
- [x] 1.2 将 allowlist 文档元数据传播到每个向量 chunk，同时保持服务器 owner/tenant 字段优先
- [x] 1.3 扩展 Java 电商 SOP fixture 与 seed 脚本，提交 knowledgeType、incident、alert、service 和 sopId
- [x] 1.4 增加上传验证、索引传播和 fixture 元数据测试

## 2. AIOps 检索角色隔离

- [x] 2.1 为 Planner 构造包含告警关联标识的 SOP 查询
- [x] 2.2 调用知识检索时固定应用 `knowledgeType=sop` metadata filter
- [x] 2.3 保持自动诊断案例为服务器控制的 `diagnostic-case` 并补充可用来源字段
- [x] 2.4 增加混合 SOP/历史案例语料测试，证明历史案例不会进入 Planner 命中和当前事实

## 3. Context Snapshot 与界面解释

- [x] 3.1 定义并持久化有限的 Planner retrieval Context Snapshot
- [x] 3.2 扩展共享 TypeScript 合同以描述可选 Snapshot
- [x] 3.3 在 AIOps 执行链展示策略、知识角色、命中来源、分数和 fallback reason
- [x] 3.4 增加 API、旧任务兼容与前端组件测试

## 4. 污染 Gate 与复盘

- [x] 4.1 增加 P3.3 离线 fixture，要求正确 SOP/告警/服务并排除历史失败词
- [x] 4.2 增加 CLI/服务回归测试并记录 Gate 使用方法
- [x] 4.3 更新 README、CHANGELOG、教程和 P3.3 版本复盘

## 5. 验证与发布

- [x] 5.1 运行 OpenSpec、后端测试、Ruff、Pyright、合同与前端测试/构建、文档构建
- [x] 5.2 完成 OpenSpec 完整性、正确性和设计一致性核验
- [x] 5.3 创建独立 P3.3 Commit、Tag 并推送 GitHub
