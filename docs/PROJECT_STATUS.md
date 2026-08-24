# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration Gate、Tenant Safe Real API Gate、应用生命周期 Gate 已由开发者本地实际执行通过；当前进入真实服务重启与生产化 Acceptance。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮从开发者反馈的 `52a9d9f` 基线继续推进，直接提交到 `main`。当前最新提交为 `38977a5`，新增 Scheduler 真实服务重启恢复 Acceptance：真实 Uvicorn 进程停止、真实 PostgreSQL Scheduler 状态持久化、进程重新启动后恢复历史 slot，并校验 Execution / Audit / Trace 关联。

开发者当前本地实际结果：

```text
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"：APP_IMPORT_OK
05_scheduler_lifecycle_gate.ps1：2 passed
针对 Scheduler 生命周期、Contract、Runtime、Trigger 的 targeted tests：36 passed
04_scheduler_tenant_misfire_gate.ps1：22 misfire unit tests、3 PostgreSQL tenant integration、6 API Contract、397 Backend regression 均通过；3 skipped，35 deselected
01_run_real_api_tests_tenant_safe.ps1：35 passed
uv run pytest -q：397 passed，3 skipped，35 deselected
```

以上结果均为开发者在当前 Scheduler 生命周期治理变更后的本地实际执行结果。新增的真实服务重启 Acceptance 尚未由开发者本地执行，因此当前不得宣称 restart recovery Gate 已通过。

## Phase 2.4 当前状态

已完成并验证：

1. Durable Scheduler Persistence / Migration；
2. Scheduler Contract / time / lease / misfire / slot 领域拆分；
3. PostgreSQL tenant isolation；
4. Runtime 持久化调度、slot claim、Execution 幂等收敛；
5. `input_data.scheduled_slot` 使用数值 interval slot，`idempotency_key` 使用统一 `scheduled:{trigger_id}:{slot}`；
6. recovery 判断使用统一 `is_recovery_slot()`，当前槽位不继承 recovery；
7. Scheduler API Contract；
8. Tenant Safe Real API：35 个真实 HTTP 测试通过；
9. FastAPI Scheduler 生命周期 Gate：启动创建唯一后台任务，退出执行 `stop → wait`，仅异常超时才取消；
10. Scheduler Execution 与真实 PostgreSQL AuditLog / WorkflowTraceEvent 的 tenant、workflow、execution 关联验收；
11. 本轮新增真实服务重启 Acceptance 自动化测试与独立 Gate，未新增第二套 Scheduler、Repository、slot key、Execution 或 Governance 实现。

## 本轮工程变更

- `tests/api_real/test_scheduler_restart_api.py`：新增真实 Uvicorn 进程停止/重启验收；通过真实 PostgreSQL 回拨持久化 `next_run_at`，验证 restart 后历史 slot 恢复为唯一 Execution，并验证 Audit/Trace tenant/workflow/execution 关联。
- `scripts/test/api-real/02_run_scheduler_restart_acceptance.ps1`：新增可重复执行的真实服务重启 Gate；自动启动临时 API 完成 tenant-safe fixture bootstrap，随后由测试自身启动/停止/重启真实 Uvicorn 进程。
- `scripts/test/api-real/README.md`：记录 restart Gate 与完整 Real API Gate 的职责边界。
- 未新增并行 Scheduler、Repository、Provider、slot key 或 Execution 实现；restart Acceptance 继续复用现有正式领域入口与 tenant-safe bootstrap。
- `docs/01-governance/DEVELOPMENT.md` 已包含重复能力前置检索、职责/规则重复检查，以及模块、类、函数/方法的中文说明和参数/返回值说明规则；本轮不创建并行治理规则。

## 下一任务

1. 本地执行 Scheduler 真实服务重启 Acceptance Gate；
2. 若通过，继续完成多实例 lease / misfire / Execution / Audit Trace 生产化 Acceptance 汇总；
3. 再执行 Backend default regression 与 Tenant Safe Real API Gate，确认完整回归无破坏；
4. 完成上述 Acceptance 后再评估 Phase 2.4 是否可以 Passed。

## 真实服务重启 Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

该 Gate 会真实启动 Uvicorn，不依赖开发者手工修改代码或测试文件；失败时脚本返回非零退出码并清理临时 fixture / 环境变量。

## 当前禁止事项

- 不标记 Phase 2.4 Passed；
- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支。
