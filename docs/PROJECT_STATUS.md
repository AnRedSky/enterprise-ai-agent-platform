# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-G Circuit Breaker 已完成开发，待开发者本地 Real API Gate 最终验收
- 当前角色：开发执行
- 测试 Gate 治理：Backend 与 Frontend Gate 已拆分，禁止单脚本跨前后端执行测试

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
| Phase 1.5-G | 开发完成，待本地 Real API 最终验收 | CLOSED / OPEN / HALF_OPEN、持久化 Circuit Policy、OPEN Fast-Fail、并发 HALF_OPEN probe quota、成功恢复、失败重新 OPEN、Retry / Timeout / Governance 边界已补齐 |
| 测试基础设施治理 | 已修复 | Backend / Frontend Gate 已拆分，Frontend 脚本位于 `frontend/`，Backend 脚本位于 `backend/` |

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

## 4. Phase 1.5-G 完成开发内容

1. `WorkflowCircuitState` 持久化模型。
2. `0020_workflow_circuit_breaker` 基础表迁移。
3. `0021_workflow_circuit_policy` 持久化 `failure_threshold` / `recovery_timeout_ms` / `half_open_max_calls`。
4. Database-backed `CircuitBreakerService`。
5. CLOSED / OPEN / HALF_OPEN 状态机。
6. `tenant_id + circuit_key` 隔离。
7. Circuit State 与 Policy 使用数据库持久化。
8. OPEN 状态 Fast-Fail。
9. HALF_OPEN probe 槽位使用行锁并在成功预约后提交，保证并发 probe quota 不超过配置。
10. HALF_OPEN probe success → CLOSED。
11. HALF_OPEN probe failure → OPEN。
12. 既有 circuit key 的 policy drift 返回 409，不允许不同 Workflow 静默改变既有 Circuit 治理参数。
13. Workflow Runtime 集成 Circuit Breaker，`CIRCUIT_OPEN` 不进入 Node Retry。
14. Real API fixture 增加并发 HALF_OPEN probe 验收，并使用独立 deterministic slow mock provider。
15. Unit Test 覆盖 policy persistence / policy drift / HALF_OPEN recovery / failure reopen / probe quota。

## 5. Phase 1.5-G Real API 验收矩阵

Real API 必须最终确认：

1. Circuit disabled 保持既有 Runtime 行为。
2. transient failure 达到 threshold 后 CLOSED → OPEN。
3. OPEN 请求立即 Fast-Fail，第二个独立 Execution 的 Node `attempt=1`。
4. OPEN Fast-Fail 不再次调用 Provider。
5. non-transient failure 不计入 failure count。
6. recovery timeout 后 OPEN → HALF_OPEN。
7. 并发 HALF_OPEN probe 数量受 `half_open_max_calls` 限制。
8. probe success 后 HALF_OPEN → CLOSED。
9. probe failure 后重新 OPEN。
10. Tenant isolation：不同 Tenant 的同名 circuit key 相互隔离。
11. Circuit OPEN 不错误消耗 Retry budget。
12. Circuit 与 Workflow Deadline / Retry 边界不互相绕过。
13. Execution / Node / Trace / Audit 最终状态一致。

当前已补齐代码和测试，尚未由本开发环境执行真实 PostgreSQL + HTTP Real API Gate，因此最终“通过”必须以开发者本地执行结果为准。

## 6. 下一步

Phase 1.5-G 本地最终验收通过后，进入下一项 Phase 1.5 Workflow / Governance 任务；不得跳过 Real API Gate，也不得恢复跨前后端的 Full Regression 脚本。
