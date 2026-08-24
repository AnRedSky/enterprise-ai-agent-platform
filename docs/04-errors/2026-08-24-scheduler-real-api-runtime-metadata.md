# 2026-08-24 Scheduler Tenant Safe Real API Gate 实测失败（二次）

## 1. 现象

开发者本地在 `2bb1d4a` 基线重新执行后：

- Application import：通过；
- Scheduler targeted tests：34 passed；
- Scheduler Tenant / Misfire Gate：全部通过，22 个 misfire unit tests、3 个 PostgreSQL tenant integration、6 个 API Contract、395 个 Backend regression 均通过；
- Tenant Safe Real API Gate：35 个测试中 3 个失败。

失败集中在 `tests/api_real/test_scheduled_trigger_api.py`：

1. `test_scheduled_trigger_create_update_invoke_and_runtime_contract_real_http`：15 秒等待窗口内未读取到预期当前 slot Execution；
2. `test_scheduled_trigger_two_workers_converge_on_one_slot_execution_real_http`：Execution 已创建，但 `input_data.scheduled_slot` 为完整 `scheduled:{trigger_id}:{slot}` 字符串，而 Contract 要求数值 interval slot；
3. `test_scheduled_trigger_recovery_slot_persists_execution_metadata_real_http`：Recovery Execution 同样将 `scheduled_slot` 持久化为完整 idempotency key 字符串，而 Contract 要求数值 interval slot。

## 2. 根因分析

### 2.1 后台 Scheduler 生命周期验收前置条件不够显式

Real API Gate 脚本只准备测试上下文并执行 pytest，本身不负责启动 API 进程。`app.main` 的 Scheduler 是否实际运行依赖被测 API 进程的 `scheduler_enabled` 配置与生命周期。当前首个测试没有 Execution，必须先确认被测 API 进程确实以 `scheduler_enabled=true` 启动，并检查 Scheduler 后台任务是否持续运行。

因此该失败不能直接归因于 PostgreSQL Runtime 逻辑，也不能通过增加更长 sleep 掩盖服务生命周期问题。

### 2.2 Scheduler Execution metadata 与 idempotency key 混用了两个概念

正式幂等键必须继续使用：

```text
scheduled:{trigger_id}:{interval_slot}
```

但 `input_data.scheduled_slot` 是执行元数据字段，应该记录纯数值 interval slot，例如：

```json
{"scheduled_slot": 26297280}
```

当前 Runtime 直接把 `slot_key` 写入 `scheduled_slot`，造成 metadata contract 与 idempotency contract 混用。

## 3. 修复边界

本轮代码修复：

- 保留 `ScheduledTriggerScheduler.idempotency_key()` 作为唯一正式幂等键入口；
- 在 Runtime 内通过既有 `interval_slot()` 计算数值 `slot_number`；
- `WorkflowExecution.idempotency_key` 继续使用完整 slot key；
- `WorkflowExecution.input_data.scheduled_slot` 改为数值 slot；
- Recovery 仍统一通过 `is_recovery_slot()` 判断，不新增第二套 recovery 规则。

没有新增 Scheduler、Repository、Provider、Execution 或第二套 slot key 实现。

## 4. 验证要求

开发者本地需要先确保真实 API 服务已经启动，并确认其 Scheduler 配置：

```powershell
cd backend
uv run python -c "from app.core.config import settings; print(settings.scheduler_enabled, settings.scheduler_poll_interval_seconds)"
```

必须看到 `True`，然后保持该 API 进程运行，再执行：

```powershell
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q tests/unit/test_workflow_scheduler_contract.py tests/unit/test_workflow_scheduler_runtime.py tests/unit/test_workflow_trigger_schedule.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\04_scheduler_tenant_misfire_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
uv run pytest -q
```

如果第一个 Real API 生命周期测试仍无 Execution，下一步应检查 API 进程启动日志中的 `scheduled-trigger-scheduler` 生命周期，而不是修改业务断言或增加第二套调度入口。

在上述结果重新执行前，Phase 2.4 不得标记为 Passed。
