## Context

P1 已经为 Chat 与 AIOps 建立 owner 范围的 Trace/Span、查询 API 和桌面时间线，但 Trace 只回答“发生了什么”，不能回答“这个版本是否比基线更好”。现有聊天消息、AIOps 报告、引用、工具审计和 Trace 指标已经包含评测所需的真实业务结果；P2 需要在不复制敏感上下文、不依赖在线 Judge、不让 CI 读取模型密钥的约束下建立可复现评分闭环。

本变更横跨 SQLite、服务层、共享合同、CLI、Vue 和 CI。真实 Agent 输出具有不确定性，因此第一阶段必须先把确定性回归规则、真实 Trace 绑定和版本对比做扎实，再为未来可选的模型 Judge 留扩展点。

## Goals / Non-Goals

**Goals:**

- 将版本化案例、真实 Agent 结果、Trace 指标、确定性检查和质量门禁组织成统一 Harness。
- 支持 Chat 与 AIOps Trace，自动从 owner 范围业务记录解析答案/报告、引用、工具和耗时。
- 持久化可审计的逐规则结果，并支持候选运行与基线运行对比。
- 提供无密钥离线 CLI 和 CI gate，使仓库自身能够证明评测流程可重复。
- 提供桌面端完整演示路径：创建数据集、选择 Trace、运行评分、定位失败、跳转 Trace。

**Non-Goals:**

- 本阶段不自动批量调用付费模型或真实 CLS；运行使用已经完成的真实 Trace，避免一次点击产生不可控云费用。
- 不实现 LLM-as-a-Judge、人工标注平台、统计显著性分析或跨仓库实验服务。
- 不把完整提示词、思维链、模型正文副本、原始工具输入输出或凭据写入评测表。
- 不承诺用确定性字符串规则衡量所有语义质量；规则只承担可解释的回归底线。

## Decisions

### 1. 使用 Trace-backed replay，而不是在评测 API 内重新调用 Agent

评测运行接收 `caseId → traceId` 绑定。服务端校验 owner、执行类型和 Trace 终态，然后从关联 Chat 会话或 AIOps 任务读取最终答案/报告，并结合 Span 计算工具、耗时和状态指标。

这比在 API 请求中直接运行模型更安全、可重复，也允许同一真实执行被多个数据集复评；代价是用户需要先产生真实 Trace。后续若加入 live runner，只需生成 Trace 后复用同一评分服务。

### 2. 规则采用封闭枚举和服务端解释

第一阶段支持 `contains_all`、`excludes_all`、`required_tools`、`min_references`、`max_duration_ms`、`max_tool_calls` 和 `trace_succeeded`。案例规则保存为 JSON，但进入服务前由 Pydantic 判别联合校验；未知规则拒绝，不能执行表达式、SQL 或用户代码。

相较任意脚本评分，这一选择牺牲灵活度，换来安全、跨平台、可解释和 CI 可重复。

### 3. 评分与门禁分层

每条规则等权产生 `0/1`；案例分数为规则平均值，所有规则通过才算案例通过。运行聚合 `passRate`、`averageScore`、`averageDurationMs`、`totalToolCalls`，再按 `minPassRate`、`minAverageScore` 和可选基线耗时回退上限生成 gate 状态。

运行本身 `completed | failed` 表示 Harness 是否执行成功；gate 使用 `passed | failed`，避免把质量失败误报为系统故障。

### 4. 数据集版本不可变，更新通过创建新版本

数据集创建时一次提交案例与规则，获得 `dataset_<uuid>` 和显式 `version`。已有数据集不提供原地修改接口；要调整规则必须创建新版本。这样历史运行始终可以解释。

名称与版本在 owner 范围唯一。删除与长期归档不在本阶段范围内。

### 5. 评测结果只保存安全证据

逐规则结果保存规则类型、通过状态和长度受限说明；案例结果只保存最多 500 字的输出摘要、聚合指标及 Trace ID。评分时会短暂读取业务正文，但不复制全文。跨用户 Trace 统一返回 404，防止资源枚举。

### 6. CLI 与服务共享纯评分内核

`super_ai.evaluation.scoring` 不依赖数据库、FastAPI、模型或环境变量。API 的 Trace 解析器和 CLI 的 JSON fixture 都构造相同 `EvaluationObservation`，调用同一评分函数。CLI 根据 gate 返回 `0/1`，并输出 JSON 报告，供 GitHub Actions 使用。

### 7. API 同步完成评分，限制案例数量

Trace replay 不调用外部服务，单次运行最多 100 个案例，因此同步 API 足够且更易演示。若未来加入 live runner，再迁移到现有 durable background job runtime。

## Risks / Trade-offs

- [字符串规则无法判断深层语义正确性] → 明确定位为回归底线；保留未来 Judge scorer 接口，不把主观评分伪装成确定事实。
- [用户可能把错误 Trace 绑定到案例] → 强制执行类型匹配，并在结果中展示资源、Trace ID 和时间，保持审计可见。
- [业务记录被删除后无法重新评分] → 已完成运行保留安全摘要与规则结果；重新运行需要仍存在的 Trace 及业务结果。
- [大量案例同步评分增加延迟] → 限制 100 个案例，仓库查询批量边界清晰；未来 live runner 使用后台任务。
- [客户端伪造指标] → API 不接受实际输出或指标，只接受 Trace ID；所有观察值由服务端 owner 范围记录解析。

## Migration Plan

1. 新增数据集、案例、运行和结果表，不修改现有业务表。
2. 上线纯评分内核、SQLite 仓库与 Trace 观察解析器。
3. 上线 owner 范围 API、共享合同和桌面工作台。
4. 加入无密钥 fixture 与 CI gate，验证本地/CI 使用同一评分逻辑。
5. 回滚时隐藏前端入口并停止新运行；新增表可独立删除，不影响 Trace、Chat 或 AIOps 数据。

## Open Questions

- LLM-as-a-Judge 的模型、校准集和成本上限在后续版本单独设计。
- live runner 是否复用后台任务以及如何隔离测试知识库留到 P3。
