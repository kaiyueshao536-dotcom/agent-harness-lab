## 1. 公开仓库卫生

- [x] 1.1 扩展 `.gitignore`，排除缓存、虚拟环境、日志、数据库、构建产物、真实配置与个人材料
- [x] 1.2 增加公开基线卫生测试，验证敏感路径不会进入 Git 索引
- [x] 1.3 审核可提交配置模板、文档示例和仓库文件名，确认不含真实凭据或个人数据

## 2. 持续集成与协作元数据

- [x] 2.1 新增无密钥 GitHub Actions workflow，运行 OpenSpec、后端和前端质量门禁
- [x] 2.2 新增 LICENSE、CONTRIBUTING.md 与 SECURITY.md
- [x] 2.3 新增 Pull Request 模板、Bug/Feature Issue 模板和仓库依赖更新配置

## 3. 项目展示文档

- [x] 3.1 重写根 README，准确展示定位、已实现能力、架构、快速开始、演示、验证、限制与路线图
- [x] 3.2 新增英文架构概览并从根 README 提供入口
- [x] 3.3 验证公开文档链接、命令和已实现能力陈述

## 4. 后端模块化

- [x] 4.1 提取 API 路由模块与依赖边界，同时保留 `super_ai.api.app:create_app` 入口及全部合同
- [x] 4.2 提取 AIOps 状态、图装配与节点辅助边界，保持 Plan-Execute-Replan-Report 行为不变
- [x] 4.3 增加模块边界和导入无副作用测试，并确认无循环导入

## 5. 验证与发布

- [x] 5.1 运行 `openspec validate --all` 和后端 Ruff、Pyright、Pytest
- [x] 5.2 运行前端类型检查、测试与构建
- [x] 5.3 初始化 Git，使用真实身份建立 Conventional Commit 基线并复核暂存集合
- [ ] 5.4 创建 `kaiyueshao536-dotcom/agent-harness-lab` 公共仓库，推送 main 并确认远端文件与 CI
