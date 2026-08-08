## ADDED Requirements

### Requirement: Controlled retrieval metadata propagation
文档上传与索引 SHALL 支持一组受控检索元数据，并将服务器验证后的字段传播到每个向量 chunk。

#### Scenario: SOP upload includes retrieval metadata
- **WHEN** 经过身份验证的 user 上传文档并提供 `knowledgeType=sop`、incident、alert、service 或 SOP 标识
- **THEN** API MUST 验证字段名称、类型和长度并持久化它们，索引器 MUST 将这些字段复制到该文档的每个 chunk metadata。

#### Scenario: Upload attempts unsafe metadata
- **WHEN** 上传 metadata 包含未知字段、非标量值或用户指定的 owner/tenant/document 标识
- **THEN** API MUST 以统一验证错误拒绝请求，MUST NOT 创建文档或索引数据。

#### Scenario: User attempts diagnostic-case role
- **WHEN** 普通知识文档上传请求指定 `knowledgeType=diagnostic-case`
- **THEN** API MUST 拒绝该角色；只有服务器端诊断案例沉淀流程可以创建该知识类型。
