# Real API：Execution 幂等测试把异步状态误判为固定 pending

## 1. 现象

Backend Regression 的 tenant-safe Real API Gate 中，`test_execution_idempotency_replays_same_execution` 失败：

```text
assert second["status"] == "pending"
AssertionError: assert 'completed' == 'pending'
```

失败发生在独立 Worker Service 已运行并消费 `pending WorkflowExecution` 的环境中。第一次创建 Execution 后，第二次使用相同 `Idempotency-Key` 请求时，Worker 可能已经完成该 Execution，因此第二次 HTTP 响应返回 `completed`。

## 2. 根因

Phase 2.5 已经把 API / Scheduler / Worker 拆成独立进程：

```text
API Service
    ↓
WorkflowExecution(status=pending)
    ↓ PostgreSQL
Worker Service
    ↓
WorkflowExecutionService.run()
```

因此 HTTP 请求之间存在真实的异步消费窗口。幂等接口返回的是同一个 `WorkflowExecution` 的当前持久化快照，而不是创建时永久冻结的 `pending` 快照。

原测试把“同一个 Execution 被幂等重放”错误实现成“第二次响应状态必须是 pending”，形成了与真实异步执行模型冲突的时序假设。

这不是生产幂等逻辑故障，也不是 Worker 进程边界故障，而是 Real API 验收断言过度约束异步状态。

## 3. 修复

将测试契约调整为：

1. 两次请求均成功返回 `201`；
2. 两次响应的 `id` 相同；
3. 两次响应的 `workflow_id` 相同；
4. 两次响应的 `idempotency_key` 相同；
5. `status` 必须属于合法 Execution 生命周期状态，但不再固定要求 `pending`。

同时在 Phase 2.5 Acceptance 中明确：

> 幂等契约保证 Execution 身份唯一，不保证异步执行期间的状态快照固定不变。

## 4. 不采用的修复

- 不暂停 Worker 以迎合测试时序；
- 不增加 `WORKER_ENABLED` 或其他进程角色开关；
- 不修改 API 返回状态来强制 `pending`；
- 不降低 Worker 消费速度；
- 不使用 Mock / JSON fixture 替代真实 PostgreSQL 链路。

这些做法都会破坏当前 Scheduler → Worker 的真实异步边界。

## 5. 本地验证

修复后必须重新执行：

```powershell
cd backend
uv run pytest -q tests/api_real/test_phase_1_9c_reliability_api.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

如果本地已运行 Worker / Scheduler，必须确认其代码来自修复后的 `main`，避免旧进程继续影响 Real API Gate 结果。
