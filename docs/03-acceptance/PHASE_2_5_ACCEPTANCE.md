# Phase 2.5 — Scheduler → Worker 执行解耦 Acceptance

## 1. 最终验收目标

验证 Scheduler 与 Workflow Runtime 已形成真实独立进程边界：

```text
Scheduler Service
    ↓ PostgreSQL pending Execution
Worker Service
    ↓ WorkflowExecutionService
WorkflowRuntime
```

## 2. 本地最终结果

### Worker targeted Unit

```text
13 passed in 1.23s
```

覆盖：

- Worker claim / dispatch；
- Worker stop；
- orphaned running Node recovery；
- ownership fencing；
- lease heartbeat；
- 首轮 heartbeat 立即 ownership check；
- heartbeat 瞬态数据库异常重试；
- lease ownership 丢失立即退出。

### Backend Regression Gate

```text
417 passed, 3 skipped, 36 deselected in 29.44s
```

### Tenant Safe Real API

```text
35 passed in 63.01s
```

### Scheduler / Worker Recovery Acceptance

真实 PostgreSQL 持久化 recovery 已通过：

```text
1 passed
```

## 3. 服务前置规则

Real API 与 Scheduler / Worker Recovery Gate 均不启动、停止或重启本地服务。

需要开发者预先分别运行：

```powershell
cd backend
uv run python run.py
```

```powershell
cd backend
uv run python run_scheduler.py
```

```powershell
cd backend
uv run python run_worker.py
```

服务角色固定：

```text
run.py           → API Service
run_scheduler.py → Scheduler Service
run_worker.py    → Worker Service
```

## 4. 最终架构断言

```text
[PASS] Scheduler 不直接执行 Runtime
[PASS] Scheduler 创建 pending Execution
[PASS] Worker 独立 claim Execution
[PASS] Worker 写入 owner / lease / attempt
[PASS] heartbeat 首轮立即检查
[PASS] lease 到期后旧 Worker 不得 resurrection
[PASS] Runtime 前恢复 orphaned running Node
[PASS] running → running 继续非法
[PASS] Manual /run 与 Worker claim 不产生第二 Runtime
[PASS] Scheduler restart / Worker recovery 使用真实 PostgreSQL
[PASS] Audit / Trace tenant/workflow/execution 关联保持一致
```

## 5. Closure

Phase 2.5 已满足本阶段验收目标，正式关闭。后续 checkpoint / durable resume 不属于本 Acceptance，而进入独立 Phase 2.6。
