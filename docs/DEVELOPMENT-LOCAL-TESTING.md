# 本地测试与 GitHub Actions 使用规则补充

> 本文件是 `docs/DEVELOPMENT.md` 的强制补充规则。若与其他文档冲突，以 `docs/DEVELOPMENT.md` 为准；本补充用于明确本项目当前测试执行方式。

## 1. GitHub Actions 禁止参与测试

本项目开发、回归、质量门禁、联调和最终验收均**不使用 GitHub Actions**。

禁止：

- 主动触发 GitHub Actions workflow；
- 通过 `push` / `pull_request` / `workflow_dispatch` 等方式提交 workflow run；
- 将 GitHub Actions workflow run、Job、Check 或 CI 状态作为测试通过依据；
- 要求开发者等待或依赖 GitHub Actions 才能继续开发。

GitHub 仓库只作为代码、文档和提交历史的存储位置，不作为本项目 CI 测试平台。

## 2. 所有测试必须提供本地流程

每个功能任务完成后，开发执行必须向验收者提供：

1. 测试前置条件；
2. 工作目录；
3. 启动 Backend / Frontend / PostgreSQL 等依赖的命令；
4. 测试命令或现有 Gate 脚本；
5. 预期关键结果；
6. 实际执行结果；
7. 失败时的错误日志和复现步骤。

不得预填测试通过结果；只有开发者实际执行并反馈后才能记录为通过。

## 3. 固定本地测试层

### Backend

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

### Frontend

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

### Browser / Frontend-Backend E2E

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Browser E2E 是独立第三层，只验证真实 Browser → Vue → Backend HTTP 用户链路，不代替 Backend 或 Frontend Gate。

## 4. 开发推进规则

本地测试未通过不得进入依赖该测试结果的下一阶段；测试通过后直接基于 `main` 继续开发，不创建功能分支。

## 5. 验收记录

`docs/PROJECT_STATUS.md` 和对应 Phase 文档只能记录实际本地执行结果。不得记录“CI 通过”“GitHub Actions 通过”作为项目验收结果。
