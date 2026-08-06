## ADDED Requirements

### Requirement: Local runtime and personal artifacts are absent from Git
仓库 SHALL 忽略本地缓存、虚拟环境、运行时日志、数据库、构建产物、真实配置、个人简历和其他非项目私有材料。

#### Scenario: Public baseline is staged
- **WHEN** 开发者从当前工作区运行 `git add .`
- **THEN** Git 索引 MUST NOT 包含 `.npm-cache`、`.python`、`.uv-cache`、虚拟环境、运行时数据库、日志、构建产物、真实配置或 `简历` 目录

### Requirement: Public baseline is audited before push
仓库 SHALL 为首次公开和后续发布提供可重复的暂存集合与敏感模式检查。

#### Scenario: Maintainer prepares a public push
- **WHEN** 维护者完成暂存但尚未推送远端
- **THEN** 维护者 MUST 检查暂存文件列表和常见凭据模式，发现真实凭据或个人数据时 MUST 阻止推送
