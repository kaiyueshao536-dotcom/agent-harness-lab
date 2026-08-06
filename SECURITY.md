# 安全策略

## 报告安全问题

请不要为疑似漏洞创建公开 Issue。请在 GitHub 仓库的 **Security → Advisories → Report a vulnerability** 中提交私密报告，包含受影响版本、复现步骤、影响和建议缓解方式。

## 凭据与数据边界

- 仓库只跟踪 `config/*.template.json`，真实本地配置必须保持 Git 忽略。
- 不得提交模型 API Key、腾讯云 CLS SecretId/SecretKey、访问令牌、密码或私有服务地址。
- 不得在日志、截图、Issue 或 Pull Request 中粘贴真实用户内容或未经脱敏的工具结果。
- 普通 GitHub Actions 不使用生产凭据，也不访问真实 CLS、LLM 或私有 MCP 服务。

## 支持范围

当前项目为个人开源演示项目，不承诺生产级安全响应 SLA。维护者会优先处理能够导致凭据泄露、跨用户数据访问、任意工具执行或权限绕过的问题。
