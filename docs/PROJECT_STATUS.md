# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B6 Delegation Multi-Worker Runtime acceptance**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- B1 Atomic Claim 已完成并通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已完成，复用既有 Workflow Worker / WorkflowRuntime；
- B3 Delegation completion/failure generation fencing 已完成；
- B4 timeout / cancel / parent semantics 已完成并由开发者本地 Real Gate 验收通过；
- Runtime Session / Execution terminalization / Model Profile Snapshot / Frontier heartbeat 锁序问题已完成修复；
- Scheduler 对单节点顺序 Workflow 的空 `edges` 语义已与 DAG Runtime 对齐；
- B5 Delegation Audit / Trace 基础闭环已实现，创建与取消事件已写入 AuditLog / WorkflowTraceEvent；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成并通过 B5 Unit Gate；
- B6 已补齐 Delegation 从 pending fact 到 Durable Frontier Worker dispatch 的正式运行链路。

## 3. 最新本地验收证据

开发者最新反馈基于 `2e73b52c`：

```text
B6 targeted Unit/Contract                        37 passed
Backend regression                                869 passed, 3 skipped, 52 deselected
Migration/head                                   0039_workflow_node_execution_tenant_trigger (head)
B6 Real Gate                                     3 passed, 1 failed
```

失败仍集中在：

```text
tests/api_real/test_agent_delegation_multi_worker_api.py::test_delegation_is_consumed_by_multiple_worker_instances_through_durable_frontier
TimeoutError: Durable Worker 未在验收等待窗口内完成本次 Delegation 集合
```

因此 **B6 尚未达到本地 Gate 通过条件，Phase 2.8 不得关闭**。

## 4. B6 实现与当前修复

B6 初始实现已把 pending Delegation 接入 Durable Frontier Worker，但本地 Real Gate 暴露多个运行时边界问题：

1. 多 Worker 两轮 dispatch 只消费了 2/4 个 Delegation；根因是并发 Claim contention 与固定轮次测试时序组合导致合法竞争被误判为任务已全部消费。
2. B2 旧 Real API 测试直接调用 `execute_claimed_execution()`，绕过了 B6 正式 Durable Frontier dispatch 边界；在 Frontier terminalization fencing 收紧后，该测试错误地让 Runtime 在仍存在 active Frontier 时直接 terminalize Execution。
3. Worker 进程关闭阶段的 AsyncEngine / asyncpg connection close 在主 Task cancellation 传播期间出现 `CancelledError`，需要保证连接池清理不被 cancellation 中断。

当前代码已完成以下修复：

1. Delegation Claim → Worker Execution → Frontier 激活使用 Claim 返回的 `worker_execution_id` 直接定位刚创建的 Frontier，不重新依赖全局 tenant Frontier 扫描；
2. B2 Real API 测试通过正式 `WorkflowWorker` Frontier Claim / Execute 边界验证 Target Agent Runtime；
3. 默认 Worker 保持 Planner-driven 正式入口，已 Claim Delegation Frontier 路由到唯一 `runtime_entry.execute_claimed_execution()`；
4. B6 Real API 首轮保留真实双 Worker Claim contention，随后在同一个 10 秒有界窗口内轮换两个独立 Worker drain 剩余 Delegation，避免固定轮次假设 PostgreSQL 调度顺序；
5. B6 超时失败改为输出本次 Delegation 的实际 durable status，不再在前一个 10 秒 drain 结束后额外重复等待 10 秒；
6. Worker AsyncEngine dispose 改为独立 Task + `asyncio.shield()`，主 Task cancellation 不再直接取消底层连接池清理；清理完成后仍恢复原 cancellation 语义，非 cancellation 异常继续传播；
7. 增加 Worker shutdown targeted unit coverage，验证正常 dispose、cancellation 下完成 dispose 以及非取消型 dispose 异常传播。

对应错误记录：

- `docs/04-errors/2026-08-29-phase-2-8-b6-worker-entrypoint-and-delegation-runtime.md`
- `docs/04-errors/2026-08-29-phase-2-8-b6-multi-worker-acceptance-contention.md`
- `docs/04-errors/2026-08-29-worker-async-engine-shutdown-cancelled-error.md`

最新修复提交：

```text
104cf240 fix(b6): harden multi-worker drain and worker shutdown cleanup
```

本地重新执行 Gate 前，不将 B6 标记为 Passed。

## 5. B6 自动化验收

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

Gate 自动生成测试用户、Token、tenant、ID 与测试数据；Gate 本身不启动、重启或停止任何服务，只验证 PostgreSQL、Redis、Backend API 本地前置条件。

验收顺序：

```text
[0] prerequisite service verification
    ↓
[1] Delegation Claim + Worker dispatch Unit/Contract
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head
    ↓
[4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
```

本轮代码修复后必须重新实际执行 Gate，不能根据代码状态预填 Passed。

## 6. 下一主线任务

```text
B6 Delegation Multi-Worker Runtime acceptance
    ↓
Phase 2.8 closure
    ↓
Phase 2.9 Enterprise Integration / Event Infrastructure Contract
```

在 B6 Real Gate 实际通过前，不提前进入 Phase 2.9 功能开发。