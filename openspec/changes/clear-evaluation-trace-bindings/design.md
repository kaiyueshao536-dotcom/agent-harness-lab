## Context

`EvaluationView.vue` 用页面级 `traceBindings` 和 `baselineRunId` 保存当前 Dataset 的运行表单。显式切换 Dataset 时，`selectDataset()` 会清理这两个状态；但 `createDataset()` 在 store 自动选中新 Dataset 后只关闭表单、清理暂存 Case，没有执行同样的运行状态重置。旧 Case ID 因而进入新 Dataset 的首次运行请求，后端按 Dataset 精确绑定边界返回 400。

## Goals / Non-Goals

**Goals:**

- 创建或切换 Dataset 后，运行表单只包含当前 Dataset 的绑定和基线。
- 保留后端对 Case 绑定集合的严格校验。
- 用前端测试覆盖真实复现顺序。

**Non-Goals:**

- 不修改 Evaluation API、数据库、评分规则或历史运行。
- 不自动迁移旧绑定，也不跨 Dataset 复用基线。
- 不重构整个 Evaluation store。

## Decisions

### 1. 在 View 层集中重置运行草稿

增加一个小型 `resetRunDraft()`，清空 `traceBindings`、`baselineRunId`，并按需要重置候选版本输入。`selectDataset()` 和 `createDataset()` 都调用该函数，避免两条路径继续漂移。

备选方案是在 store 的 `createDataset()` 中清理，但 Trace 绑定属于 View 的表单状态，store 不拥有该对象；将它下沉会扩大接口和测试范围。

### 2. 新建完成后不保留旧基线

Dataset 版本不可变，Baseline 必须属于同一 Dataset。即使名称或 Case 相似，也不能猜测旧基线可复用，因此创建新版本后固定清空。

### 3. 保留后端拒绝多余 Case ID

前端修复提升体验，后端校验仍是权限和数据一致性的最终边界，不能通过放宽服务校验掩盖状态错误。

## Risks / Trade-offs

- [候选版本标签也被重置会增加重复输入] → 本次只清理绑定和基线，保留候选标签，避免不必要的交互变化。
- [未来新增运行草稿字段可能再次遗漏] → 测试以创建和切换两条入口的行为为中心，并让重置函数成为唯一入口。
