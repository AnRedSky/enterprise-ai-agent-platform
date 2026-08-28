# 2026-08-28 Phase 2.7 Real API：Durable Frontier Claim 未推进 Execution Running

## 1. 实际现象

开发者在 `8d642a1` 执行 tenant-safe Real API Gate，结果：

```text
7 failed, 34 passed in 199.22s
```

上一轮已经修复 Runtime Governance 的非法 `edges: []` fixture 与失败 Node Durable Fact 丢失问题；本轮剩余 Resume / Resume DAG / Resume Failure 真实 Worker 场景仍无法在超时窗口内进入期望终态。

## 2. 根因

Durable Frontier Worker 的 Claim 事务已经取得 `WorkflowExecution` ownership、`worker_attempt` 与 lease，但 pending Execution 在 Claim 成功后仍保持 `pending`。

与此同时，`complete_frontier_with_checkpoint()` 的正式成功契约要求关联 Execution 必须已经处于 `running`：

```text
Claim Frontier
    ↓
Execution ownership / lease
    ↓
Execution 必须 running
    ↓
Node Runtime
    ↓
Frontier progression
    ↓
frontier_completed Checkpoint / Next Frontier / terminalization
```

默认 Worker 已切换为 Planner-driven Durable Frontier Worker 后，旧的 `runtime_entry` pending→running 转换不再覆盖 Planner-driven 的自定义 `execute_frontier()` 路径，形成了 Claim 生命周期与 completion contract 之间的断层。

该问题尤其影响 Resume Execution：Resume Bootstrap 正确创建 `pending` Resume Execution 与首个 Frontier，但 Worker Claim 后没有在同一 Claim 事务完成 Execution lifecycle 初始化，导致后续 Frontier Runtime 与 completion contract 不能稳定收敛。

## 3. 修复

直接在 `DurableFrontierWorkflowWorker.claim_one_frontier()` 的同一事务内完成：

1. Claim Frontier；
2. 设置 Execution owner / lease / fencing attempt；
3. pending Execution → running；
4. 首次启动写入 `started_at`；
5. 写入 `execution.state_changed -> running` Trace；
6. Frontier → running；
7. 一次 commit。

expired running Execution 回收到 pending 后同样经过该统一启动边界。

不调用会提前 `commit()` 的通用 `WorkflowExecutionService.transition()`，因此不会破坏 Claim → Runtime → Frontier progression 的原子边界；也没有新增第二套 Runtime 状态机。

## 4. 环境边界

本次开发者反馈同时存在多个旧 Worker 进程。Real API 验收必须先停止所有旧 Worker，只启动当前 `main` 代码的一个 Worker；Scheduler 验收默认也只启动一个当前 `main` Scheduler。否则旧进程可能继续消费当前测试生成的 Durable Frontier，导致结果无法证明当前代码。

## 5. 必须执行的验证

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

# 1. Worker Durable Frontier targeted Unit
uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q

# 2. Runtime Governance
uv run pytest tests/api_real/test_runtime_model_governance_api.py -q -m real_api

# 3. Resume targeted Real API
uv run pytest `
  tests/api_real/test_workflow_resume_api.py `
  tests/api_real/test_workflow_resume_dag_api.py `
  tests/api_real/test_workflow_resume_failure_api.py `
  -q -m real_api

# 4. Scheduler targeted Real API
uv run pytest tests/api_real/test_scheduled_trigger_api.py -q -m real_api

# 5. Tenant-safe 全量 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Unit 必须先通过；Real API 结果必须以开发者本地实际执行结果为准，不得预填 PASS。
