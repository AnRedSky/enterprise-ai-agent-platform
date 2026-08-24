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

本轮基于远端 `main` 最新提交 `bb300a8` 继续开发。此前 Scheduler Tenant / Misfire Gate 已通过，最新开发者本地实际反馈进一步确认 Tenant Safe Real API Gate **35 passed**，Scheduler 的真实 HTTP + PostgreSQL 持久化链路当前无已知阻塞。

开发者本地最新实际结果：

```text
uv run python -c "from app.core.config import settings; print('scheduler_enabled=', settings.scheduler_enabled); print('scheduler_poll_interval_seconds=', settings.scheduler_poll_interval_seconds)"：scheduler_enabled=True，poll=5.0
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"：APP_IMPORT_OK
Scheduler targeted tests：34 passed
04_scheduler_tenant_misfire_gate.ps1：22 misfire unit tests、3 PostgreSQL tenant integration、6 API Contract、395 Backend regression 均通过；3 skipped，35 deselected
01_run_real_api_tests_tenant_safe.ps1：35 passed
```

## Phase 2.4 当前状态

已完成并验证：

1. Durable Scheduler Persistence / Migration；
2. Scheduler Contract / time / lease / misfire / slot 领域拆分；
3. PostgreSQL tenant isolation；
4. Runtime 持久化调度、slot claim、Execution 幂等收敛；
5. `input_data.scheduled_slot` 使用数值 interval slot，`idempotency_key` 使用统一 `scheduled:{trigger_id}:{slot}`；
6. recovery 判断使用统一 `is_recovery_slot()`，当前槽位不继承 recovery；
7. Scheduler API Contract；
8. Tenant Safe Real API：35 个真实 HTTP 测试全部通过。

本轮继续推进应用生命周期工程化：

- `app/main.py` 补充中文模块职责与 `lifespan` / `health` 函数说明，明确 Scheduler 启停副作用和边界；
- 新增 `tests/unit/test_app_lifespan.py`，验证 `scheduler_enabled=true/false` 两种生命周期行为；
- 新增 `scripts/test/integration/05_scheduler_lifecycle_gate.ps1`，形成可重复执行的生命周期 Gate；
- 开发准则进一步强化重复实现前置检索、职责/规则重复检查、代码说明完整性和提交前审查要求。

## 下一任务

当前不再修复已经通过的 Tenant Safe Real API Contract，直接进入 Scheduler 生产化 Acceptance：

1. 生命周期 Gate；
2. 多实例 lease；
3. skip / fire_once / catch_up 真实持久化恢复；
4. Execution / Audit Trace 关联；
5. restart recovery；
6. 完成后再评估 Phase 2.4 是否可以 Passed。

## 当前禁止事项

- 不标记 Phase 2.4 Passed；
- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支。
