# 本地测试与验收指南

> 本文只描述本地测试入口与测试职责，不记录当前 Phase 状态。当前状态统一见 `docs/PROJECT_STATUS.md`。

## 1. Backend

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

Backend 四层测试：

```text
unit
integration
api_contract
api_real
```

## 2. Frontend

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

## 3. Browser E2E

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Browser Gate 只负责浏览器、真实 Frontend、真实 Backend HTTP 用户链路。

## 4. Real API

Real API 唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

Token、Workflow ID、Execution ID 等测试 context 必须由 bootstrap 自动准备，不得手工填写并提交。

## 5. 测试结果记录

测试结果只有在开发者实际执行并反馈后才能写入 `PROJECT_STATUS.md` 或对应 Acceptance。计划、预期结果和历史结果不得伪装成当前通过。

## 6. 目录职责

```text
backend/tests/ = 测试实现
backend/scripts/test/ = Backend Gate 编排
frontend/tests/ = Frontend 测试实现
frontend/scripts/test/ = Frontend / Browser Gate 编排
```

Backend / Frontend / Browser 三层 Gate 独立执行；不得重新创建跨技术栈 Full Regression Gate。