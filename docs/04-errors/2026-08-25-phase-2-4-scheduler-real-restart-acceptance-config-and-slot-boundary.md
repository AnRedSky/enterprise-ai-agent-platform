# Phase 2.4 Scheduler Real Restart Acceptance：配置校验与 interval slot 边界错误

## 1. 发生时间

2026-08-25

## 2. 范围

Phase 2.4 Scheduler 真实服务重启验收，以及 Tenant Safe Real API Scheduler Trigger 验收。

## 3. 现象

### 3.1 Real Restart Acceptance

`02_run_scheduler_restart_acceptance.ps1` 首次执行时，真实 HTTP 创建 Scheduled Trigger 返回 `422`：

```text
只有 catch_up 策略允许配置 catch_up_limit
```

测试请求同时设置了：

```text
misfire_policy = fire_once
catch_up_limit = 1
```

该配置违反当前 Trigger Contract：`catch_up_limit` 只允许与 `catch_up` 策略一起配置。

### 3.2 Tenant Safe Real API

`01_run_real_api_tests_tenant_safe.ps1` 同时暴露一个已有真实 API 测试的 interval 边界竞态：

```text
test_scheduled_trigger_create_update_invoke_and_runtime_contract_real_http
AssertionError: []
```

测试在 HTTP 创建 Trigger 后立即使用独立的 `datetime.now(UTC)` 计算目标 slot。Scheduler 的真实后台轮询可能在计算过程中跨过 60 秒 interval 边界，导致测试计算的幂等键与真实 Scheduler 根据 PostgreSQL 持久化 `next_run_at` 产生的 slot 不一致。

这不是 Scheduler 生产算法需要修改的问题，而是 Real API 测试错误地用测试进程当前时间推断后台持久化 Scheduler 的实际 slot。

## 4. 根因

1. Restart Acceptance 测试请求使用了不合法的 `misfire_policy + catch_up_limit` 组合。
2. Real API Trigger 测试没有以真实 Trigger 对应的 Execution / PostgreSQL 持久化状态作为 slot 观测源，而是使用测试进程瞬时时钟计算 slot，形成 interval 边界竞态。

## 5. 修复

### 5.1 Restart Acceptance

保留 `fire_once` 的单次恢复语义，删除不适用于该策略的 `catch_up_limit` 参数，使请求遵循现有 Trigger Contract，而不是修改生产校验规则。

### 5.2 Real API Slot 观测

新增按 Trigger 前缀读取真实 PostgreSQL `workflow_executions.idempotency_key` 的测试辅助入口：

```text
scheduled:{trigger_id}:{slot}
```

测试先等待该 Trigger 的真实 Execution 产生，再从真实持久化幂等键解析 slot，并验证：

- 幂等键属于当前 Trigger；
- slot 与 `input_data.scheduled_slot` 一致；
- `recovery` 为 false；
- 同一幂等键再次轮询不会产生第二条 Execution。

这样测试不再复制 Scheduler 的当前时间计算逻辑，也不会因为测试线程跨越 interval 边界而观察到错误 slot。

## 6. 影响范围

本次修复仅修改 Real API 测试实现，没有修改 Scheduler Runtime、Scheduler Repository、Trigger Contract 或 PostgreSQL Schema。

## 7. 验证要求

必须在开发者本地重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\05_scheduler_lifecycle_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\04_scheduler_tenant_misfire_gate.ps1
uv run pytest -q
```

本记录只记录已经实际发生的错误与代码修复；上述重新验证结果在开发者执行前不得记录为通过。
