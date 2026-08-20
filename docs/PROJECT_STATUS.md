# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- 当前阶段：Phase 1.5 Workflow / Governance
- 当前任务：Phase 1.5-G Circuit Breaker Real API 边界验收与失败修复复测
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
| Phase 1.5-G | 阻塞复测中 | Circuit Breaker 已落地 main；Real API Fast-Fail attempt 边界仍待开发者复测确认 |
| 测试基础设施治理 | 已修复待本地静态验收 | 原错误的跨前后端 Full Regression 脚本已删除，Backend / Frontend Gate 已拆分为两个独立脚本 |

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
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\02_frontend_regression_gate.ps1
```

Real API 唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

不得恢复一个同时调用 `uv run pytest` 与 `npm test` / `npm run build` 的 `Full Regression Gate`。

## 4. 本轮测试基础设施治理变更

本轮已直接提交 `main`：

1. 删除 `backend/scripts/test/release/01_full_regression_gate.ps1`，消除跨前后端测试耦合。
2. 新增 `backend/scripts/test/release/01_backend_regression_gate.ps1`，只负责 Backend regression → Migration/head → Real API。
3. 新增 `backend/scripts/test/release/02_frontend_regression_gate.ps1`，只负责 Frontend test → production build。
4. 更新 `docs/DEVELOPMENT.md`，正式禁止跨前后端测试 Gate 脚本。
5. 新增 `docs/error-tracking/009-test-gate-backend-frontend-coupling.md`，记录本次工程错误、根因、影响、修复和验证要求。

以上仅完成脚本/文档结构修复；本轮尚未由开发者本地重新执行两个独立 Gate，因此不得标记测试通过。

## 5. Phase 1.5-G 当前实现与验收

Phase 1.5-G 已提交 main：

1. `WorkflowCircuitState` 持久化模型。
2. `0020_workflow_circuit_breaker` Alembic migration。
3. Database-backed `CircuitBreakerService`。
4. CLOSED / OPEN / HALF_OPEN 状态机。
5. `tenant_id + circuit_key` 隔离。
6. Circuit 状态读取与更新使用数据库行锁。
7. `failure_threshold`、`recovery_timeout_ms`、`half_open_max_calls` 配置校验。
8. OPEN 状态 Fast-Fail。
9. HALF_OPEN probe 槽位限制。
10. Workflow Runtime 集成 Circuit Breaker。
11. 仅 transient failure 计入熔断阈值；404 / 403 / 422 等业务/权限类错误不应触发熔断。
12. Circuit Breaker Unit Test 与 Runtime Contract Test。

Real API 必须覆盖：

1. Circuit disabled 保持既有 Runtime 行为。
2. transient failure 达到 threshold 后 CLOSED → OPEN。
3. OPEN 请求立即 Fast-Fail，不再次调用 Provider。
4. non-transient failure 不计入 failure count。
5. recovery timeout 后 OPEN → HALF_OPEN。
6. HALF_OPEN probe 数量受 `half_open_max_calls` 限制。
7. probe success 后 HALF_OPEN → CLOSED。
8. probe failure 后重新 OPEN。
9. Tenant isolation：不同 Tenant 的同名 circuit key 相互隔离。
10. Circuit OPEN 不错误消耗 Retry budget。
11. Circuit 与 Workflow Deadline / Retry 边界不互相绕过。
12. Execution / Node / Trace / Audit 最终状态一致。

## 6. 本轮实际测试反馈

开发者本地最新反馈：

```text
Real API Gate
9 passed, 1 failed

test_circuit_breaker_opens_and_fast_fails_real_business_boundary
second_nodes[0]["attempt"] == 2, expected 1
```

该失败仍未通过本地复测确认解决，Phase 1.5-G 保持阻塞复测状态。

## 7. 当前下一步

1. 开发者同步最新 `main`。
2. 分别执行 Backend Regression Gate 与 Frontend Regression Gate，验证两个脚本的实际运行边界。
3. 继续定位 Phase 1.5-G Real API `second_nodes[0]["attempt"] == 2` 问题。
4. 全部相关 Gate 实际通过后，再更新 Phase 文档并收口 Phase 1.5-G。

禁止因为脚本结构修复而提前宣称 Phase 1.5-G 或全量测试通过。
