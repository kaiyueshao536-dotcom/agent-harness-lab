## ADDED Requirements

### Requirement: Knowledge-role metadata filtering
知识检索工具 SHALL 将请求的 `knowledgeType` 等 metadata filter 同时应用于 tenant 范围的向量和 BM25 候选，未满足角色的 chunk 不得进入融合或 rerank。

#### Scenario: AIOps requests only SOP knowledge
- **WHEN** AIOps 使用 `metadata.knowledgeType=sop` 调用检索工具
- **THEN** 向量命中和 BM25 命中 MUST 在融合前排除 `diagnostic-case` 与普通 `document`，最终结果和引用 MUST 只包含 SOP。

#### Scenario: Filter removes every candidate
- **WHEN** 当前 tenant 没有满足 metadata filter 的 chunk
- **THEN** 工具 MUST 返回空结果且 MUST NOT 将未过滤候选发送给 rerank。
