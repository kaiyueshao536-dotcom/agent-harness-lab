## Why

用户在已有 Dataset 留有 Trace 绑定时创建新 Dataset，页面会把旧 Case 的绑定继续带入首次运行请求，后端因绑定集合不属于新 Dataset 而正确拒绝。该问题来自前端跨 Dataset 状态未清理，会让用户误以为新建的评测集或真实 Trace 不合法。

## What Changes

- 在创建并选中新 Dataset 后立即清理旧 Case 的 Trace 绑定和旧基线。
- 保证切换 Dataset 与创建 Dataset 使用同一套运行表单重置语义。
- 增加前端回归测试，覆盖“旧 Dataset 已绑定 Trace → 创建新 Dataset → 首次运行”的真实复现路径。
- 在版本记录中说明问题、后端保护边界和修复验证。

## Capabilities

### New Capabilities

- `evaluation-workspace-state`: 约束自动评测工作台在 Dataset 创建或切换时隔离运行表单状态，禁止提交属于其他 Dataset 的残留绑定或基线。

### Modified Capabilities

无。

## Impact

- 影响 `apps/frontend/src/views/EvaluationView.vue` 的 Dataset 创建完成状态清理。
- 影响自动评测前端组件测试，不修改后端 API、数据库结构、评分规则或历史 Dataset。
- 修复不重新调用模型、MCP 或 CLS，不产生云端费用。
