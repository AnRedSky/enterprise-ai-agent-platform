# 2026-08-25：Worker Claim 与 HTTP `/run` 重复 Runtime 竞态

## 1. 现象

开发者本地 Tenant Safe Real API Gate 在 Circuit Breaker Half-Open 并发场景出现：

```text
POST /workflows/executions/<id>/run
-> 409: Node 不允许从 running 到 running
```

Worker 日志同时出现：

```text
Workflow Worker execution failed
...
WorkflowExecutionService.transition_node(..., "running")
...
HTTPException: 409: Node 不允许从 running 到 running
```

此前相同测试还出现过 `/run` 返回 `503 Circuit Breaker is open` 或 `409 只有 pending Execution 可以 Run`，说明测试观察层存在合法 Worker claim 竞态，但 `running -> running` 属于生产执行所有权竞争，需要修复，不能继续当作普通测试竞态吞掉。

## 2. 根因

当前 Worker claim 流程是：

```text
Worker claim_one()
    ↓ PostgreSQL row lock
worker_owner = Worker A
status = pending
commit
    ↓
Worker execute_claimed()
    ↓
WorkflowExecutionService.run()
```

原来的 `WorkflowExecutionService.run()` 只判断：

```text
status == pending
```

没有判断 `worker_owner` 是否已经被当前调用方持有。

因此存在如下时序：

```text
T1 Worker A claim
   worker_owner=A, status=pending

T2 HTTP /run 读取同一 Execution
   status=pending

T3 HTTP /run transition
   pending -> running

T4 Worker A transition
   pending -> running

T5 Runtime 第一个 Node
   Node 已经被另一 Runtime 推进为 running
   ↓
   running -> running
   ↓
   409
```

这不是 Node 状态机应该放宽的问题，而是 Execution Runtime ownership 没有贯穿到 `run()` 入口。

## 3. 修复

### 3.1 ExecutionService 增加执行者 owner 校验

`WorkflowExecutionService.run()` 新增 `worker_owner` 参数：

- HTTP `/run` 不传 owner；
- Worker 传入自己的 owner；
- Execution 未被 Worker claim 时，HTTP `/run` 正常执行；
- Execution 已被 Worker claim 时，只有持有相同 owner 的 Worker 可以进入 Runtime；
- HTTP `/run` 遇到已 claim 的 pending Execution 返回原有 `409 只有 pending Execution 可以 Run` Contract，不重复执行；
- 不修改 Node 状态机，不增加 `running -> running`。

### 3.2 Worker 贯穿 owner

`WorkflowWorker.execute_claimed()` 调用：

```text
WorkflowExecutionService.run(..., worker_owner=self.owner)
```

从而使 claim、Execution 状态转换、Node 状态转换使用同一个 ownership 身份。

## 4. 为什么不是修改 Node 状态机

不能把：

```text
running -> running
```

加入合法状态转换。

这样会把两个 Runtime 同时执行同一个 Node 的问题隐藏起来，并可能导致：

- Provider 重复调用；
- Usage Record 重复计费；
- Circuit Breaker 配额判断失真；
- Trace / Audit 重复写入；
- 输出数据存在 last-write-wins 覆盖。

正确边界是：

```text
Execution ownership
        ↓
唯一 Runtime owner
        ↓
唯一 Node transition
```

## 5. 测试覆盖

新增 Unit 断言：

1. Worker owner 与数据库不一致时旧 Worker 被 fencing；
2. 当前 Worker owner 可以继续执行；
3. HTTP 手动 `/run` 遇到已 claim Execution 必须拒绝；
4. 未 claim Execution 允许 HTTP `/run`；
5. 非当前 Worker owner 不允许进入 Runtime。

已有 Real API `run_or_observe_execution()` 继续只处理测试观察层的合法 `pending` claim 竞态，不放宽生产状态机。

## 6. 本地验收

```powershell
cd backend

uv run pytest -q tests/unit/test_workflow_execution_worker_fencing.py tests/unit/test_workflow_worker.py

uv run pytest -q

uv run alembic upgrade head
uv run alembic current

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Real API / Scheduler Gate 必须使用开发者本地已经运行的 API、Worker、Scheduler 与 PostgreSQL；Gate 脚本不启动、停止或重启服务。

## 7. 当前状态

代码修复已经直接提交 `main`。本地测试结果必须以开发者重新执行后的实际输出为准，未执行前不得标记 Acceptance Passed。
