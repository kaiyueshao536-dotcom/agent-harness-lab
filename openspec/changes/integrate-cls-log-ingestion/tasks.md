## 1. 依赖与安装

- [x] 1.1 为官方 CLS SDK 覆盖不兼容的旧压缩依赖并更新 `uv.lock`
- [x] 1.2 在当前 Windows/Python 3.11 环境执行 `uv sync` 和导入检查

## 2. 公共 CLS ingestion 服务

- [x] 2.1 实现显式初始化、可注入客户端的结构化日志上传服务
- [x] 2.2 实现批次边界、来源字段和敏感键拒绝
- [x] 2.3 添加配置、LogGroup 构建、脱敏和客户端调用单元测试

## 3. 测试日志脚本

- [x] 3.1 重构 fixture 上传脚本以复用公共服务
- [x] 3.2 增加 `--dry-run` 和不含凭据的上传摘要
- [x] 3.3 添加脚本参数与 dry-run 测试

## 4. LogListener 与 SDK 接入文档

- [x] 4.1 新增 Linux/Windows Server LogListener 安装、机器组、JSON 文件采集与检查指南
- [x] 4.2 记录业务服务 SDK 调用方式、来源字段和避免重复采集规则
- [x] 4.3 更新真实日志与告警教程，加入 dry-run、上传和 SearchLog 验收命令

## 5. 验证

- [x] 5.1 运行后端 pytest、Ruff、Pyright 和 OpenSpec 校验
- [x] 5.2 对已配置的腾讯云测试主题显式上传安全 fixture
- [x] 5.3 通过真实 CLS SearchLog 验证日志数量、时间和来源元数据
