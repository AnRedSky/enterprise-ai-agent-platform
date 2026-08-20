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
- 最新测试门职责调整：已移除重复的 Frontend/Backend 全套质量门脚本，统一由 Release / Full Regression Gate 编排

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
| Phase 1.5-G | 阻塞复测中 | Circuit Breaker 已落地 main；本地 Real API 发现 Retry Audit、Runtime 异常包装及 Fast-Fail attempt 边界问题，已提交修复，等待开发者重新执行全部门禁 |
| 测试基础设施治理 | 持续治理 | Unit / Integration / API Contract / Real API 四层规范持续执行；重复的 Frontend/Backend Gate 已移除，Full Regression 统一归入 Release Gate |

## 3. 测试 Gate 结构

```text
Unit → Integration → API Contract → Real API → Frontend Test/Build
                                                ↓
                                      Release / Full Regression
                                                ↓
                                  Browser / Frontend-Backend E2E
```

Backend 默认回归：

```powershell
cd backend
uv run pytest -q
```

Release / Full Regression 唯一全套编排入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_full_regression_gate.ps1
```

Real API 唯一入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

`backend/scripts/test/integration/` 当前仅作为未来真正 Frontend / Backend E2E 编排层保留；不得重新加入重复的 Backend、Migration、Real API、Frontend Test/Build Gate。

## 4. 本轮测试基础设施治理变更

已直接提交 `main`：

1. 删除 `backend/scripts/test/integration/01_frontend_backend_gate.ps1`。
2. 新增 `backend/scripts/test/release/01_full_regression_gate.ps1`，承接 Backend regression → Migration/head verification → Real API → Frontend test/build 的全套质量门编排。
3. 更新 `backend/scripts/test/integration/README.md`，明确该目录不是重复质量门入口，未来只承载真正 Browser / Frontend-Backend E2E 编排。
4. 更新 `docs/DEVELOPMENT.md`，移除已删除的联调唯一入口，建立 Release / Full Regression Gate 规则。
5. 本次结构调整不删除 `backend/tests/integration`、`backend/tests/api_real` 或 `backend/scripts/test/api-real`。

## 5. 已验收基线

### Backend / Retry Reliability

此前 Workflow Runtime Timeout / Failure Recovery、Node Retry / Attempt、Retry Budget、Retry Deadline 等链路曾通过；本轮开发者反馈重新执行时发现 `test_run_exhausts_retry_budget_before_scheduling_retry` 回归失败，原因与终态异常包装有关，已修复，尚待本地复测确认。

### Migration

Phase 1.5-G 新增：

```text
0020_workflow_circuit_breaker
```

该 migration 已提交到 main。按照开发准则，必须由开发者本地实际执行 `uv run alembic upgrade head` 后才可标记验收通过。

### Real API

本轮开发者实际反馈：

- `test_node_retry_real_business_loop`：失败，缺少 `workflow.node.retry` Audit action。
- `test_circuit_breaker_opens_and_fast_fails_real_business_boundary`：失败，第二个独立 Execution 的首个 `CIRCUIT_OPEN` Node 观测为 `attempt=2`，预期为 1。

已提交 Runtime 修复：

- 新建 Node Execution 显式 `attempt=1`。
- Retry scheduling 同时保留 `workflow.node.retry` 与 `workflow.node.retry_scheduled`。
- Execution 已进入 terminal state 后不再把原始 Runtime 异常二次包装成 HTTP 500。

修复提交：`e0fff63ca6fdd56cb40bd7bb03f28b779b34d7a3`。

以上修复尚未由当前环境重新执行本地 Real API 验证，因此不得标记 Phase 1.5-G 通过。

### Frontend

此前 Frontend tests 与 production build 均通过；Phase 1.5-G 无独立 Circuit Breaker UI，但修复完成后仍需重新执行前端测试与 production build 作为阶段门禁。

## 6. Phase 1.5-G Circuit Breaker 当前实现

已提交 main：

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

设计原则与项目架构中的 `Timeout + Retry + Circuit Breaker` 容错要求一致；熔断状态外置到 PostgreSQL，保持 Runtime worker 无状态并支持多副本共享状态。

## 7. Phase 1.5-G 验收要求

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

## 8. 本轮实际测试反馈

开发者本地实际反馈：

```text
uv run pytest -q
204 passed, 1 failed, 10 deselected

Real API Gate
8 passed, 2 failed

Full Regression Gate
Backend regression failed，因此后续 Gate 被阻断
```

失败已记录至：

```text
docs/error-tracking/008-phase-1-5-g-real-api-retry-and-circuit-boundary.md
```

## 9. 当前修复提交与复测要求

已直接提交 `main`：

```text
e0fff63ca6fdd56cb40bd7bb03f28b779b34d7a3
fix: preserve runtime failures and retry governance audit
```

当前不能声称 Phase 1.5-G 已通过。开发者必须同步最新 `main` 后重新执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\migration\01_migrate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
cd ..\frontend
npm test
npm run build
cd ..\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_full_regression_gate.ps1
```

若复测仍出现 `second_nodes[0]["attempt"] == 2`，下一步必须直接检查本地真实数据库中该 `execution_id` 对应的 `workflow_node_executions` 行、创建时间、状态转换 Trace 与 API 请求关联，禁止仅修改断言掩盖问题。

## 10. 下一步

**当前唯一优先工作项：完成 Phase 1.5-G 修复后的本地 Real API 边界复测，并定位/修复任何残留的 HALF_OPEN / attempt / 并发探针配额问题。**

只有全部门禁实际通过后：

1. 更新本文件收口 Phase 1.5-G。
2. 更新 `docs/14-phase-1.5-g-circuit-breaker.md` 的实际验收结果。
3. 进入 Workflow Execution 查询列表与历史执行治理。
4. 再进入异步 Worker / 调度能力。
