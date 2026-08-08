# P4：上下文路由、预算与质量 Gate

## 这次解决的真实问题

P3.3 已经阻止历史诊断案例进入 Planner，但一次真实 `PaymentGatewayTimeoutHigh` 诊断仍召回三份正式 SOP：正确的支付超时 SOP、网关熔断 SOP 和搜索 ES 超时 SOP。三者知识角色都是 `sop`，所以仅靠 `knowledgeType=sop` 不能判断它们是否属于当前告警。

错误 SOP 会占用模型上下文，并增加模型把其他服务故障关联到当前支付告警的风险。P4 的目标不是搭建通用记忆平台，而是回答三个可验证的问题：

1. 哪些候选真正进入了 Planner？
2. 为什么某个候选被选中或排除？
3. 本次 SOP 正文用了多少上下文预算？

## 第一次真实验收暴露的第二个问题

代码上线后的第一次真实运行并没有排除搜索 ES SOP。Context Snapshot 给出了直接证据：5 个候选全被标记为 `generic`，因为旧 Milvus chunk 缺少 `alertName` 和 `service` 元数据。算法无法根据不存在的数据判断冲突。

这不是继续调分数能解决的问题，而是一次历史数据迁移未闭环：P3.3 已修改上传和索引代码，但本机旧向量没有自动获得新字段。重新执行 Java 电商 SOP seed/reindex 后，第二次运行才得到预期结果。

面试时可以把它概括为：**代码兼容旧数据保证系统可用，但严格路由能力依赖元数据回填；测试不仅要验证新写入，还要验证存量数据。**

## 选择策略

P4 在 SOP-only 检索结果上增加确定性路由层级：

1. `alert-match`：SOP 告警名与当前告警一致；
2. `service-match`：告警名未精确匹配，但服务一致；
3. `generic`：旧 SOP 缺少路由元数据，保留兼容性；
4. `metadata-conflict`：SOP 的告警或服务与当前诊断冲突，直接排除。

同一层级仍保持 Rerank 顺序。Planner 最多使用 3 个来源、1600 个近似 Token；如果第一份合格 SOP 超预算，可以安全截断，后续超预算候选则排除。这里使用的是 LangChain 的确定性近似计数，不冒充模型厂商账单 Token。

## Context Snapshot 记录什么

策略版本为 `sop-budget-v1`。Snapshot 记录候选的来源、分数、亲和度、选择决策、原因、估算/使用 Token 和是否截断，同时记录总预算和实际用量。

它不保存 SOP 正文、完整 Prompt、模型思维链、MCP URL、Topic ID 或凭据。旧 `sop-only` Snapshot 仍能正常展示。

## Evaluation 如何形成闭环

P4 新增三个确定性规则：

- `required_context_sources`：正确 SOP 必须进入上下文；
- `excluded_context_sources`：已知无关 SOP 不得进入上下文；
- `max_context_tokens`：上下文不得超过预算。

旧 Trace 没有预算字段时，`max_context_tokens` 会明确失败并显示 `None`，不会把“缺失”伪装成 0。Gate 仍只能检查 Dataset 中声明的规则，不能自动发现所有未知污染。

## 真实数据结果

同一支付告警形成了修复前后两条 Trace：

| 指标 | 元数据回填前 | 元数据回填后 |
| --- | ---: | ---: |
| Trace | `trace_210491db40664bc0a501fdf22cddaff4` | `trace_224e144cd4654e8bb444c1bd364a91e9` |
| 候选 / 进入上下文 | 5 / 3 | 5 / 1 |
| 上下文近似 Token | 872 | 284 |
| 搜索 ES SOP | 错误进入 | `metadata-conflict`，已排除 |
| Gate | 失败 | 通过 |
| 平均分 | 80% | 100% |
| 端到端耗时 | 117,905 ms | 114,723 ms |

修复后相对失败 Baseline：通过率 `+100 pt`、平均分 `+20 pt`、耗时 `-2.6988%`、工具调用变化 `0`。

## 如何复现

离线 Gate 不调用模型、Milvus、MCP 或 CLS：

```powershell
cd apps/backend
uv run super-ai-eval ../../evals/fixtures/p4-context-quality-pass.json
```

真实验收前需要让旧 SOP 获得路由元数据：

```powershell
cd apps/backend
uv run python scripts/seed_java_ecommerce_aiops_sops.py --profile java-ecommerce
```

随后从“智能诊断”选择 `PaymentGatewayTimeoutHigh`，在 Planner 执行链中核对候选、排除原因和 Token 预算，再在“自动评测”绑定新 Trace 运行 P4 Dataset。
