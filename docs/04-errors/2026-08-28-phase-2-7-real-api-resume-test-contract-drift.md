# 2026-08-28 Phase 2.7 Real API：Resume 验收路径与 DAG Fixture Contract 漂移

## 1. 实际现象

最新 `main` 的本地 Tenant Safe Real API Gate 在多 Worker + Scheduler 已允许并发执行后出现 5 个失败：

- `test_real_api_persists_governed_usage_and_calculated_cost`
- `test_real_worker_executes_durable_resume_from_checkpoint`
- `test_real_worker_executes_full_linear_dag_after_resume`
- `test_real_worker_resume_dag_failure_after_frontier_preserves_checkpoint_and_lease`
- `test_real_worker_resume_failure_preserves_lineage_and_source_terminal_state`

## 2. 根因

### 2.1 Resume Real API 测试绕过正式 Bootstrap Contract

项目已经将 Durable Resume 的正式交付边界定义为：

```text
Source Execution lock
    ↓
Resume creation
    ↓
completed Node lineage copy
    ↓
first Durable Frontier enqueue
    ↓
atomic commit
```

正式入口是 `WorkflowExecutionResumeContractService.resume_with_outcome()`，其内部调用 `WorkflowExecutionResumeBootstrapService`，保证 Resume Execution 创建后立即存在可消费 Frontier。

部分 Real API Worker 验收测试却直接调用 `WorkflowExecutionService.resume_from_latest_checkpoint()`。该方法负责创建 pending Resume Execution，但不负责正式 Bootstrap；因此测试产生了没有首个 Frontier 的 pending Resume Execution，Worker 没有 durable work item 可以消费，最终等待超时。

这属于测试调用路径与当前正式 Domain Contract 漂移，不是要求 Worker 在没有 Frontier 的情况下猜测 Resume 任务。

### 2.2 Usage Accounting fixture 仍使用历史 `edges: []`

当前 Workflow DAG Contract 要求发布的 DAG Definition 具有非空 `edges`。Usage Accounting Real API fixture 仍创建单节点 `edges: []` Definition，因此发布接口返回：

```text
422: DAG Workflow 必须包含非空 edges
```

该 fixture 已改为最小合法 DAG：

```text
prepare(input) → usage-agent(agent)
```

## 3. 修复

1. Durable Resume / Resume DAG / Resume Failure Real API 验收统一通过 `WorkflowExecutionResumeContractService` 创建 Resume。
2. 保留真实 PostgreSQL、真实 HTTP Provider Fixture 与独立 Worker 验收边界。
3. Resume DAG 测试显式验证 Bootstrap 复制的 `prepare` completed Node lineage，同时继续验证 `provider-call` / `finish` 的实际 Resume execution。
4. Usage Accounting fixture 改为当前合法的最小两节点 DAG。
5. 不修改 Worker 的多实例约束；多个 Worker 仍然允许同时运行，Scheduler 也必须存在并参与真实验收。

## 4. 验收边界

Real API Gate 的前置服务要求保持：

- PostgreSQL：`localhost:5432`
- Redis：`localhost:6379`
- API Service：`127.0.0.1:8000`
- Worker Service：至少 1 个当前 `main` Worker；允许多个 Worker 并发运行
- Scheduler Service：至少 1 个当前 `main` Scheduler；允许多个 Scheduler 并发运行

Gate 不启动、停止或重启这些服务。

## 5. 下一步验证

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q

uv run pytest `
  tests/api_real/test_workflow_resume_api.py `
  tests/api_real/test_workflow_resume_dag_api.py `
  tests/api_real/test_workflow_resume_failure_api.py `
  -q -m real_api

uv run pytest tests/api_real/test_runtime_model_governance_api.py -q -m real_api
uv run pytest tests/api_real/test_usage_accounting_api.py -q -m real_api
uv run pytest tests/api_real/test_scheduled_trigger_api.py -q -m real_api

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

以上命令必须以开发者本地实际执行结果作为验收依据，不预填 PASS。
