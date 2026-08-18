# 提交规范

## 分支

- `main`：稳定基线。
- `feature/phase-x.y`：阶段开发分支。
- 不直接向 `main` 提交功能代码。

## Commit

使用 Conventional Commits：

```text
feat: 新功能
fix: 缺陷修复
docs: 文档
refactor: 重构
test: 测试
chore: 工程维护
```

Commit 应描述单一逻辑变化，避免将无关修改混在同一个提交中。

## Pull Request

PR 必须说明：

1. 上一阶段完成情况。
2. 本 PR 当前完成内容。
3. 测试与验证结果。
4. 风险与已知限制。
5. 下一阶段待办。

## 禁止提交

禁止提交以下非项目文件：

- `.env` / API Key / 密码 / Token
- `node_modules/`
- `dist/`、coverage、缓存
- `.venv/`、`__pycache__/`
- IDE / OS 临时文件
- 本地日志
- 临时截图
- 临时 ZIP / TAR / 备份文件
- 与项目无关的个人文件

## 阶段验收

代码开发完成后必须先：

```text
本地测试 → GitHub 文件完整性 → CI → PR Review
```

只有上一阶段达到可复现、可测试、可审查状态后，才能开始下一阶段。
