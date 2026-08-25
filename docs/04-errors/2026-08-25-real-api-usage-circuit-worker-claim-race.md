# 2026-08-25：Real API Usage / Circuit Breaker 与独立 Worker 竞争竞态

## 1. 发生现象

开发者在 `bfb0014` 后执行 Tenant Safe Real API Gate，首次反馈两个失败：

```text
tests/api_real/test_usage_accounting_api.py::test_real_api_persists_governed_usage_and_calculated_cost
-> POST /workflows/executions/<id>/run
-> 409: 只有 pending Execution 可以 Run
```

以及：

```text
tests/api_real/test_workflow_governance_api.py::test_circuit_breaker_half_open_probe_quota_real_business_boundary
-> expected [200, 503]
-> actual [409, 409]
```

同一轮 Backend Regression Gate 随后在一次完整重跑中已经反馈：

```text
35 passed in 58.94s
[PASS] Tenant-safe Real API gate completed.
[PASS] Backend regression gate completed.
```

但该通过结果发生在上述代码修复提交之后的另一次本地执行中，不能替代本次新增测试代码修改后的本地验证。

## 2. 根因

### 2.1 Usage Accounting 的 `/run` 竞争

当前 Phase 2.5 执行链是：

```text
POST create Execution
    ↓
status = pending
    ↓
独立 Worker 使用 PostgreSQL claim
    ↓
WorkflowRuntime 执行
```

Real API 测试创建 `pending` Execution 后直接调用 `/run`，独立 Worker 可能已经先完成 claim。因此 `/run` 返回：

```text
409: 只有 pending Execution 可以 Run
```

这不是生产状态机错误，也不应通过放宽 `running → running`、自动 resume 或重复执行来“修复”。

### 2.2 Circuit Breaker Half-Open 的两个 409

Half-Open 测试并发创建两个 `pending` Execution，再分别调用 `/run`。独立 Worker 可以在两个 HTTP `/run` 到达前先行 claim 两个 Execution。

因此两个 HTTP 请求都可能看到 `pending` 已经被消费，均返回 409；但真正需要验证的业务边界是：

```text
两个并发 Probe
    ↓
Circuit Half-Open quota
    ├── 一个 Probe 获得执行资格 → completed / HTTP 200 语义
    └── 一个 Probe 被拒绝       → failed / CIRCUIT_OPEN / HTTP 503 语义
```

因此仅断言 `/run` 的瞬时 HTTP 状态会把 Worker 调度竞争与 Circuit Breaker 业务结果混在一起。

## 3. 修复

新增：

```text
backend/tests/api_real/execution_helpers.py
```

统一提供 `run_or_observe_execution()`：

1. 首先调用真实 HTTP `/run`；
2. 返回预期状态时直接返回真实响应；
3. 若返回精确的 `只有 pending Execution 可以 Run`，视为 Worker 合法抢占；
4. 通过真实 HTTP 查询 Execution，等待 PostgreSQL 持久化进入终态；
5. 不改变生产 `/run` Contract；
6. 不启动、停止或重启任何服务；
7. 其他 409、其他 HTTP 错误以及超时直接失败。

Usage Accounting 测试改为验证：

```text
/run = 200 或合法 Worker claim 409
最终 Execution = completed
Usage Record = 真实 PostgreSQL 持久化
```

Circuit Breaker Half-Open 测试在 Worker claim 409 时根据真实持久化终态恢复业务语义：

```text
completed + claim-race → 200 业务语义
failed + CIRCUIT_OPEN + claim-race → 503 业务语义
```

仍严格要求最终结果为 `[200, 503]`，不会把任意 409 当作通过。

## 4. 为什么不修改生产状态机

当前生产设计明确禁止：

```text
running → running
```

并且 Worker ownership fencing 用于阻止 stale consumer。让 `/run` 接受已经被 Worker claim 的 Execution 会产生重复执行风险，因此本问题属于 Real API 测试观察方式与异步执行模型不一致，而不是生产状态机需要放宽。

## 5. 验收要求

本次代码修改后必须在开发者本地重新执行：

```powershell
cd backend
uv run pytest -q tests/api_real/test_usage_accounting_api.py tests/api_real/test_workflow_governance_api.py

uv run pytest -q

uv run alembic upgrade head
uv run alembic current

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

其中 Real API / Scheduler Gate 必须使用开发者本地实际运行的 API、Worker、Scheduler 与 PostgreSQL；测试脚本不得控制这些服务的生命周期。
