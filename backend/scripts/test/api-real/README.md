# Real API Test Gate

唯一入口：`01_run_real_api_tests.ps1`。

前置条件由 `00_bootstrap_real_api.py` 自动通过真实 HTTP 注册/登录并准备 Workflow/Execution，禁止手工设置 Token/ID。

当前 Real API Gate 覆盖：

- 基础 Workflow / Version / Execution / Trace / Audit HTTP 验收。
- Node Retry / Attempt。
- Retry Budget Exhausted。
- Workflow Deadline 与 Retry Delay 边界。
- Circuit Breaker：transient failure → OPEN、OPEN Fast-Fail、HALF_OPEN recovery、成功探活后 CLOSED。
- Scheduler Scheduled Trigger 的真实 HTTP、PostgreSQL 持久化、tenant isolation、misfire、slot 幂等以及 Execution / Audit / Trace 关联。

Real API Fixture 使用 deterministic Mock Provider，测试不会依赖外部真实模型 Provider。测试结束后 `.real_api_context.json` 与相关环境变量必须清理。

Real API Gate 是 Release / Full Regression Gate 的强制前置质量门；不得由其他测试脚本复制其 Bootstrap/Fixture 逻辑。

## Scheduled Trigger 定向 Real API Gate

为避免直接执行 `test_scheduled_trigger_api.py` 时遗漏 `TRIGGER_WORKFLOW_ID` tenant-safe 上下文，提供独立 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\06_run_scheduled_trigger_real_tests.ps1
```

该 Gate 自动执行 source baseline、API/Worker/Scheduler 服务基线检查、tenant-safe Bootstrap、Admin fixture，再运行 Scheduled Trigger Real API 测试。它不会启动、停止或重启任何服务。

服务要求：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`；
- API Service：`127.0.0.1:8000`；
- Worker：当前 `main` 且仅 1 个项目 Worker；
- Scheduler：当前 `main` 且仅 1 个项目 Scheduler。

因此不再建议直接使用以下命令作为 Scheduled Trigger 验收入口：

```powershell
uv run pytest tests/api_real/test_scheduled_trigger_api.py -q -m real_api
```

直接 pytest 需要调用者自行提供 `ACCESS_TOKEN`、`TRIGGER_WORKFLOW_ID` 等上下文；缺失时的 fail-fast 不是产品功能失败。

## Scheduler 真实服务重启 Acceptance

Scheduler 生产化 Acceptance 使用独立入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

该 Gate 复用既有 tenant-safe bootstrap，不复制 Fixture；随后由测试自身启动真实 Uvicorn 进程，停止进程、直接检查并修改真实 PostgreSQL Scheduler 持久化状态，再重新启动进程，验证历史 slot 可以恢复为唯一 WorkflowExecution，并保持 AuditLog / WorkflowTraceEvent 的 tenant、workflow、execution 关联。

该 Gate 与 `01_run_real_api_tests_tenant_safe.ps1` 职责独立：前者专门验证跨真实进程的 Scheduler restart recovery，后者验证完整 Real API regression。
