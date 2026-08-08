## 1. 前端状态修复

- [x] 1.1 在 EvaluationView 集中实现运行草稿清理，并在 Dataset 切换和创建完成后调用
- [x] 1.2 保留后端精确 Case 绑定校验与现有候选版本输入行为

## 2. 回归测试

- [x] 2.1 增加“旧绑定后创建新 Dataset”组件测试，证明首次运行只提交新 Case ID
- [x] 2.2 保留并验证已有 Dataset 切换清理、API 合同和评测工作台测试

## 3. 验证与发布记录

- [x] 3.1 运行前端测试、类型检查、构建和 OpenSpec 校验
- [x] 3.2 更新 CHANGELOG、P3.3.1 复盘与版本索引
- [x] 3.3 创建独立 Commit、Tag 并推送 GitHub
