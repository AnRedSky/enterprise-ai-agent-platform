# Phase 1.6-C：Frontend / Backend Integration & Browser E2E Contract

> 本阶段建立 Backend Contract、Frontend Contract 之外的第三独立测试层。依据 `docs/DEVELOPMENT.md`，Browser / Frontend-Backend E2E 不复制 Backend regression、Migration、Real API 或 Frontend regression。

## 1. 阶段目标

验证 Workflow Trigger Governance 从真实浏览器入口到真实 Backend HTTP 的完整用户链路：

```text
Browser
  ↓
Vue 3 UI
  ↓
Frontend API client
  ↓
FastAPI HTTP
  ↓
Workflow Trigger Service
  ↓
Workflow Execution
  ↓
PostgreSQL
```

本阶段只验证已有 Phase 1.6-A / 1.6-B Contract，不扩展 MQ、Worker、Cron、Event Bus、Temporal 或其他 Workflow Engine 能力。

## 2. E2E Contract

测试场景：

1. 注册隔离 E2E 用户并登录。
2. 通过真实 Backend HTTP 创建 draft Workflow。
3. 创建 Workflow Version 并发布。
4. 浏览器打开 `/login`，通过真实 UI 登录。
5. 进入 `/workflows/triggers`。
6. 选择 Published Workflow。
7. 通过 UI 创建 manual Trigger。
8. 验证 Trigger 为 enabled。
9. 通过 UI Invoke Trigger。
10. 验证最近一次 Execution 为 completed。
11. Disable Trigger。
12. 验证 UI 禁止 Invoke。
13. Re-enable Trigger。
14. Delete Trigger。
15. 验证 Trigger 从 UI inventory 消失。

治理边界同时验证：

- Tenant 不由前端提交。
- UI 通过 Trigger API，不直接调用 Execution Runtime。
- Disabled Trigger 的 Invoke action 在 UI 层不可用。
- Execution 结果来自真实 Backend response。

## 3. 实现范围

### Frontend

```text
frontend/playwright.config.ts
frontend/tests/e2e/workflow-trigger-governance.spec.ts
frontend/scripts/test/e2e/01_run_workflow_trigger_e2e.ps1
frontend/package.json
```

Browser 测试使用 Playwright。测试 fixture 通过 Playwright APIRequestContext 调用真实 Backend HTTP；用户操作通过真实浏览器页面完成。

### 依赖

`frontend/package.json` 增加：

```text
@playwright/test
```

首次安装依赖后需安装 Chromium：

```powershell
cd frontend
npm install
npx playwright install chromium
```

## 4. 运行条件

E2E 不自动启动 Backend，也不自动执行 Frontend regression。运行前需要：

```powershell
cd backend
uv run python run.py
```

另一个终端启动 Frontend：

```powershell
cd frontend
npm run dev
```

然后：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

可通过环境变量覆盖地址：

```text
FRONTEND_BASE_URL=http://127.0.0.1:5173
API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## 5. Gate 隔离

```text
Backend Gate
  Backend regression
  → Migration/head
  → Backend Real API

Frontend Gate
  Frontend Vitest
  → production build

E2E Gate
  Browser
  → real Frontend
  → real Backend HTTP
```

E2E Gate 不调用：

- `uv run pytest`
- Alembic migration
- Backend Real API Gate
- `npm test`
- `npm run build`

## 6. 当前验收状态

**开发实现已提交，但 E2E Gate 尚未由开发者本地执行，因此当前不得标记为通过。**

必须以本地实际执行结果更新本文件和 `docs/PROJECT_STATUS.md`。

## 7. 后续关闭条件

Phase 1.6-C 关闭前必须：

1. 安装 Playwright Chromium。
2. 启动真实 Backend 与 Frontend。
3. 执行 E2E Gate。
4. E2E 全部通过。
5. 独立 Backend Gate 通过。
6. 独立 Frontend Gate 通过。
7. 更新项目状态和本 Phase 文档。
8. 提交 `main`。
