## 1. 上下文选择与预算

- [x] 1.1 新增可单测的 SOP 元数据亲和度、近似 Token 预算和安全截断选择器
- [x] 1.2 将选择器接入 AIOps Planner，保持 SOP-only、审计、退化计划和 owner 范围
- [x] 1.3 扩展 Context Snapshot，记录候选、决策、原因、预算和实际选中来源

## 2. 合同与界面解释

- [x] 2.1 扩展共享 TypeScript 合同并兼容旧 `sop-only` Snapshot
- [x] 2.2 在 AIOps 执行链展示 P4 策略、Token 预算、选中与排除来源
- [x] 2.3 增加前端组件和共享合同测试

## 3. Evaluation 上下文质量 Gate

- [x] 3.1 扩展 Evaluation rule/observation/scoring，支持必需来源、禁止来源和最大上下文 Token
- [x] 3.2 从 owner 范围 AIOps Planner step 解析 Context Snapshot，并保持旧 Trace 可解释失败
- [x] 3.3 扩展 API/前端 Rule Builder、CLI fixture 和后端回归测试

## 4. 验证与真实闭环

- [x] 4.1 运行 P4 离线 Gate、后端测试、Ruff、Pyright、合同/前端测试与构建、OpenSpec 校验
- [x] 4.2 重启本地服务并用 PaymentGatewayTimeoutHigh 验证支付 SOP 保留、搜索 ES SOP 排除和预算可见
- [x] 4.3 创建 P4 真实 Trace Dataset，记录 Gate、来源精度、Token 体量和端到端耗时

## 5. 发布与复盘

- [x] 5.1 更新 README、CHANGELOG、P4 学习教程和版本复盘
- [x] 5.2 创建独立 P4 Commit、Tag 并推送 GitHub
