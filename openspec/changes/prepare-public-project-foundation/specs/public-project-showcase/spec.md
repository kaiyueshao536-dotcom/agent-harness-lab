## ADDED Requirements

### Requirement: Repository homepage communicates the implemented system
公共仓库 SHALL 提供面向首次访问者的根 README，准确说明项目定位、已实现能力、架构、快速开始、验证命令、演示流程、限制和路线图。

#### Scenario: Recruiter opens the repository homepage
- **WHEN** 访问者未阅读源代码而打开根 README
- **THEN** 页面 MUST 能区分已实现能力与未来计划，并在一个入口内提供架构和本地运行路径

### Requirement: Public collaboration and security metadata
公共仓库 SHALL 提供许可证、贡献指南、安全披露策略、Pull Request 模板和 Issue 模板。

#### Scenario: External contributor prepares a change
- **WHEN** 贡献者准备报告问题、安全缺陷或提交 Pull Request
- **THEN** 仓库 MUST 提供对应的流程、验证命令和禁止提交凭据的说明

### Requirement: Architecture documentation supports international review
公共仓库 SHALL 提供简体中文主文档和至少一份英文架构概览，且两者不得宣称未实现的能力。

#### Scenario: English-speaking reviewer evaluates the project
- **WHEN** 访问者通过 README 进入英文架构概览
- **THEN** 文档 MUST 说明核心组件、Agent 执行路径、数据边界、验证方式和已知限制
