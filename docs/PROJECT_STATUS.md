# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration Gate、Tenant Safe Real API Gate 已通过；当前进入生命周期与生产化 Acceptance。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮从开发者反馈的 `446a47c` 基线继续推进，随后直接提交到 `main`。当前最新提交为 `b385268`，包含 Scheduler 应用生命周期优雅退出与 Execution / Audit / Trace 真实持久化关联验收增强。

开发者此前本地实际结果仍为：

```text
uv run python -c "from app.core.config import settings; print('scheduler_enabled=', settings.scheduler_enabled); print('scheduler_poll_interval_seconds=', settings.scheduler_poll_interval_seconds)"：scheduler_enabled=True，poll=5.0
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"：APP_IMPORT_OK
Scheduler targeted tests：34 passed
04_scheduler_tenant_misfire_gate.ps1：22 misfire unit tests、3 PostgreSQL tenant integration、6 API Contract、397 Backend regression 均通过；3 skipped，35 deselected
01_run_real_api_tests_tenant_safe.ps1：35 passed
```

上述结果属于代码修改前开发者实际执行结果；本轮新增代码后的测试尚未由本地开发环境重新执行，因此不得据此宣称本轮变更已通过。

## Phase 2.4 当前状态

已完成并验证：

1. Durable Scheduler Persistence / Migration；
2. Scheduler Contract / time / lease / misfire / slot 领域拆分；
3. PostgreSQL tenant isolation；
4. Runtime 持久化调度、slot claim、Execution 幂等收敛；
5. `input_data.scheduled_slot` 使用数值 interval slot，`idempotency_key` 使用统一 `scheduled:{trigger_id}:{slot}`；
6. recovery 判断使用统一 `is_recovery_slot()`，当前槽位不继承 recovery；
7. Scheduler API Contract；
8. Tenant Safe Real API：35 个真实 HTTP 测试全部通过；
9. Scheduler 应用生命周期已有独立 Gate，且本轮进一步强化正常关闭路径的 `stop → wait` 语义；
10. Real API Scheduler 测试增加 Execution 与真实 PostgreSQL AuditLog / WorkflowTraceEvent 的 tenant、workflow、execution 关联断言。

本轮工程变更：

- `app/main.py`：Scheduler 正常退出先调用 `stop()` 并等待后台任务自然完成；仅在超时情况下取消任务，避免正常生命周期路径依赖强制取消；
- `tests/unit/test_app_lifespan.py`：增加后台任务完成态断言，验证生命周期等待语义；
- `tests/api_real/test_scheduled_trigger_api.py`：增加真实 PostgreSQL Audit / Trace 查询与关联断言，并保持既有多实例、misfire、restart idempotency 验收；
- 未新增第二套 Scheduler、Repository、slot key、Execution 或 Governance 实现；继续复用现有正式领域入口；
- 当前 `docs/01-governance/DEVELOPMENT.md` 已包含重复能力前置检索、职责/规则重复检查、中文模块/函数说明、参数/返回值说明等规则，本轮不重复创建并行治理规则文档。

## 下一任务

本轮代码完成后，必须由本地开发环境重新执行 Scheduler 生命周期、Backend Regression、Tenant/Misfire Gate 与 Tenant Safe Real API Gate，确认上述新增验收没有破坏既有 Contract。

通过后继续：

1. 多实例 lease / misfire / Execution / Audit Trace Acceptance；
2. restart recovery 的真实服务生命周期验收，而不仅是进程内重新实例化 Scheduler；
3. 完成生产化 Acceptance 后再评估 Phase 2.4 是否可以 Passed。

## 当前禁止事项

- 不标记 Phase 2.4 Passed；
- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支。
