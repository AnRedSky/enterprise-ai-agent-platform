# 项目仓库地址

- GitHub：https://github.com/AnRedSky/enterprise-ai-agent-platform.git
- 默认分支：`main`

## 开发基线

后续整改、实现与验收均以远端 `main` 的最新提交为基线。提交前先确认本地工作区已同步 `main`，避免基于旧分支继续开发。

## 测试与脚本职责

继续遵守现有 `tests / scripts` 职责隔离：测试用例放在 `tests/`，测试编排脚本放在 `scripts/test/`，开发运行脚本不与测试入口混用。
