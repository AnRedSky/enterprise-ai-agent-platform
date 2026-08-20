# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- 当前阶段：**Phase 1.6 Workflow Production Hardening**
- 当前任务：**Phase 1.6-A Workflow Trigger Contract，待开始 Backend Contract 实现**
- 当前角色：开发执行
- 测试 Gate 治理：Backend 与 Frontend Gate 已拆分，禁止单脚本跨前后端执行测试
- 规范核查：已完成，详见 `docs/14-project-compliance-audit-and-correction-plan.md`

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5-A | 已完成 | Workflow Definition Contract，本地 Backend 验收通过 |
| Phase 1.5-B | 已完成 | Publish Governance、Tenant Contract，本地 Backend 手工验收通过 |
| Phase 1.5-C | 已完成 | Workflow Execution State Machine，本地 Backend 验收通过 |
| Phase 1.5-D | 已完成 | Workflow Runtime Integration；本地验收无异常 |
| Phase 1.5-E | 已完成 | Governance / Audit / Trace；全量测试通过，warning 已修复并验收通过 |
| Phase 1.5-F | 已完成 | Cancel / Retry / Retry lineage / Idempotency-Key / Execution Concurrency / Timeout / Failure Recovery / Node Retry / Attempt / Retry Budget / Workflow Deadline 治理已完成并通过 Real API 边界验收 |
| Phase 1.5-G | **已完成** | CLOSED / OPEN / HALF_OPEN、持久化 Circuit Policy、OPEN Fast-Fail、并发 HALF_OPEN probe quota、成功恢复、失败重新 OPEN、Retry / Timeout / Governance 边界已完成；Backend pytest、migration/head、Real API Gate 全部通过 |
| Phase 1.5 | **已完成** | A～G 全部完成；不再重复开发 Circuit Breaker，进入后续生产化建设 |
| 测试基础设施治理 | 已修复 | Backend / Frontend Gate 已拆分，Frontend 脚本位于 `frontend/`，Backend 脚本位于 `backend/` |
| Phase 1.6-A | 待开始 | Workflow Trigger Contract；下一项执行任务 |

## 3. 测试 Gate 结构

```text
Backend Gate（独立）
Backend regression → Migration/head → Real API

Frontend Gate（独立）
Frontend test → production build

Browser / Frontend-Backend E2E（独立层，当前未实现）
```

Backend 默认回归：

```powershell
cd backend
uv run pytest -q
```

Backend Regression Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Frontend Regression Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

Real API 唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

不得恢复一个同时调用 `uv run pytest` 与 `npm test` / `npm run build` 的 `Full Regression Gate`。

## 4. Phase 1.5-G Real API 验收结果

开发者本地真实 PostgreSQL + HTTP Real API Gate 已完成，结果如下：

### Migration

```text
uv run alembic upgrade head
INFO  Running upgrade 0020_workflow_circuit_breaker -> 0021_workflow_circuit_policy, persist circuit breaker policy
```

### Backend Regression

```text
uv run pytest -q
209 passed, 11 deselected in 3.44s
```

### Real API Gate

```text
scripts/test/api-real/01_run_real_api_tests.ps1
11 passed in 17.62s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

因此 Phase 1.5-G 的本地验收门禁全部通过，Phase 1.5 正式关闭。

## 5. 规范核查与纠偏记录

本次远端 `main` 整体核查形成：

- `docs/14-project-compliance-audit-and-correction-plan.md`：项目规范核查、完成度对照、偏差修正与后续规划。
- `docs/error-tracking/002-backend-frontend-test-gate-coupling.md`：记录 Backend / Frontend Gate 跨栈耦合错误。
- `docs/error-tracking/003-circuit-breaker-state-initialization.md`：记录 Circuit Breaker 新建状态计数初始化缺陷。
- `docs/15-phase-1.6-workflow-production-hardening-plan.md`：建立 Phase 1.6 下一阶段执行基线。

本次核查确认：

1. Backend / Frontend 测试必须继续完全独立。
2. 测试脚本必须位于所属技术栈目录内。
3. Browser / Frontend-Backend E2E 未来作为第三独立测试层。
4. Phase 1.5-G 已完成，不再重复开发 Circuit Breaker。
5. 总体架构中尚未完成的 MQ / Worker、Multi-Agent、Evaluation、复杂审批、可视化 Workflow 等能力不得提前标记完成。

## 6. Phase 1.6-A 下一步执行

下一项任务为 **Workflow Trigger Contract**，具体基线见 `docs/15-phase-1.6-workflow-production-hardening-plan.md`。

第一步只允许进入 Backend：

```text
远端 main 最新基线
→ Backend Trigger Domain + API Contract
→ Migration（如需要）
→ Backend pytest / API Contract
→ Backend Real API scenario
→ 再进入 Frontend API Type / Vitest / UI
```

Phase 1.6-A 暂不实现 MQ / Worker / Cron / Event Bus / Temporal 等分布式能力，不复制 Workflow Runtime 逻辑，Trigger 必须复用现有 Execution State Machine、Idempotency、Concurrency、Reliability、Audit / Trace 治理。

完成后必须分别执行 Backend Gate 与 Frontend Gate，并更新本文件、Phase 文档及 error-tracking，最后直接提交 `main`。
