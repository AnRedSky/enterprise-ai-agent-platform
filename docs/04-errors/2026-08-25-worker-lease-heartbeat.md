# Worker Lease Heartbeat 瞬时异常导致租约刷新任务退出

## 1. 发现范围

- 日期：2026-08-25
- Phase：2.5 Scheduler → Worker 执行解耦
- 组件：`backend/app/services/workflow_worker/runtime.py`
- 类型：Worker 运行时可靠性缺陷

## 2. 问题

原 Worker 在 `_renew_lease_forever()` 中直接执行数据库查询和提交，没有对单轮 heartbeat 的非取消异常进行隔离。

因此一次 PostgreSQL 连接瞬时失败、连接池抖动或事务异常会直接终止 heartbeat 协程，而 Runtime 主执行协程仍继续运行。由于 heartbeat 任务由 `create_task()` 创建，原实现不会在异常发生的瞬间把失败显式反馈给 Worker 主执行路径；最终可能出现：

```text
Worker claim
    ↓
lease heartbeat
    ↓
一次瞬时 DB 异常
    ↓
heartbeat task 退出
    ↓
Runtime 继续执行
    ↓
lease 到期后可能被其他 Worker 接管
    ↓
旧 Worker 后续状态写入由 ownership fencing 拒绝
```

这不会放宽 `running → running` 状态机，但会扩大 ownership 生命周期不稳定窗口，并使 heartbeat 失败原因不具备清晰日志。

## 3. 根因

heartbeat 生命周期与 Runtime 生命周期已经解耦，但单轮刷新异常没有被设计为“可重试的基础设施瞬态错误”。同时，`finally` 中等待 heartbeat task 时只显式处理 `CancelledError`，如果 heartbeat task 因未处理异常退出，也可能覆盖原 Runtime 结果。

## 4. 整改

本轮不修改 Worker ownership Contract，也不实现 `running Execution` checkpoint/resume。

采用以下边界：

1. 新增 `_renew_lease_once()`，把单轮数据库刷新拆成可测试的原子动作；
2. `_renew_lease_forever()` 捕获单轮非取消异常，记录中文上下文日志后继续下一轮；
3. `CancelledError` 继续向上层传播，保证正常 Worker shutdown 不被吞掉；
4. 当数据库查询发现当前 owner 已不存在、Execution 已进入终态或已被其他 Worker 接管时，heartbeat 立即退出；
5. heartbeat 间隔改为 `max(0.1, lease / 3)`，避免极短 lease 下第一次刷新恰好落在 lease 边界；
6. 不通过延长 lease、降低 polling 或修改 Node 状态机规避并发问题。

## 5. 设计边界

```text
heartbeat transient DB failure
        ↓
记录日志 + 下一轮重试

ownership 已失效
        ↓
heartbeat 退出
        ↓
后续 Runtime 状态转换由 ownership fencing 拒绝
```

本整改不把 heartbeat 失败转换成自动 Execution resume，也不允许旧 Worker 在 ownership 失效后继续写入业务状态。

## 6. 验证要求

必须执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_worker.py tests/unit/test_workflow_execution_worker_fencing.py tests/unit/test_workflow_worker_lease_heartbeat.py
```

随后执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

并继续执行既有：

```powershell
cd backend
uv run python .\scripts\dev\inspect_worker_runtime_consistency.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

## 7. 结果记录规则

本文件只记录工程错误与整改设计，不预填测试通过结果。最终通过状态以开发者本地实际执行反馈为准。
