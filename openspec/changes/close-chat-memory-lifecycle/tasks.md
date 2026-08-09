## 1. 数据模型与迁移

- [x] 1.1 为 Chat session 增加版本化 memory snapshot、状态、错误分类和最近尝试字段，并完成 Alembic 迁移
- [x] 1.2 扩展 repository record、SQLite 映射与 owner-scoped 原子更新接口，兼容旧 `memory_summary`
- [x] 1.3 定义 Pydantic v2 结构化记忆模型、候选解析、来源校验和确定性覆盖规则

## 2. Trace、失败恢复与流式正确性

- [x] 2.1 将 Chat Trace 创建移动到记忆准备之前，记录 prepare/compact/validate/agent 层级 Span 与安全 attributes
- [x] 2.2 先持久化稳定 user message，再压缩其之前的历史；保存记忆准备状态并支持复用 message id 重试
- [x] 2.3 增加独立压缩超时、有限重试和失败状态，保证失败不推进边界或替换旧快照
- [x] 2.4 修复 LangChain 重叠内容事件导致的回答重复，并增加 service 层防重保护
- [x] 2.5 扩展共享 SSE/API contract，发出 memory stage 与可重试错误信息

## 3. API 与桌面 Chat 页面

- [x] 3.1 扩展 session memory payload，安全返回版本、状态、边界、active/superseded 条目与来源
- [x] 3.2 增加 owner-scoped failed-message retry API，并覆盖越权和幂等场景
- [x] 3.3 在桌面 Chat 页面展示压缩阶段、最近状态、当前约束、已废止事实、来源和失败重试动作

## 4. Memory Evaluation Harness

- [x] 4.1 扩展评测模型与 repository，支持版本化 Chat memory Case 期望和故障类型
- [x] 4.2 实现约束保留、旧值泄漏、无来源事实、重复输出、压缩成功与耗时的确定性评分
- [x] 4.3 将 memory 指标接入现有 Baseline/Gate 聚合与 API/页面结果展示
- [x] 4.4 提供 A—D 类可重复 fixture，覆盖显著约束、旧值覆盖、有规律和不可推导长上下文

## 5. 验证与文档

- [x] 5.1 增加后端 migration/repository/service/API/Trace/Evaluation 测试与前端 store/component 测试
- [x] 5.2 运行 pytest、Ruff、Pyright、前端测试、build 和 `openspec validate --all`
- [x] 5.3 更新 README、学习复盘和 `docs/version-history/p5-chat-memory-lifecycle.md`
- [x] 5.4 完成真实桌面浏览器验收，记录压缩成功、覆盖、失败保护、Trace 与 Gate 结果
