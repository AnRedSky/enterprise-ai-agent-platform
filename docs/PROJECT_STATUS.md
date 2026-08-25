# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler restart acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**核心代码实现完成；Worker ownership fencing、orphaned running Node recovery、Scheduler/Worker Recovery Acceptance 已形成实现与验收闭环，当前仅剩本轮 Real API Gate 重新执行确认。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮工作基线：`6aa0657 fix(worker): recover orphaned running nodes before runtime`。

该基线已经完成 Worker Recovery Boundary：不修改 Node 状态机合法转换，在 Worker 正式进入 Runtime 前恢复 `pending Execution + running Node` 遗留状态。

```text
API Service       run.py
Scheduler Service run_scheduler.py
Worker Service    run_worker.py
```

服务角色由启动入口固定确定，不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 切换角色。

## 当前产品级执行架构

完整产品设计记录：

```text
docs/00-architecture/WORKFLOW_WORKER_EXECUTION_ARCHITECTURE.md
```

```text
API / Trigger
      ↓
Scheduler Service
      ↓
PostgreSQL pending WorkflowExecution
      ↓
Worker claim
      ↓
worker_owner + lease + attempt
      ↓
ownership fencing
      ↓
recover orphaned running Node
      ↓
lease heartbeat
      ↓
WorkflowExecutionService
      ↓
WorkflowRuntime
      ↓
Node / Execution terminal state
      ↓
Audit / Trace / ownership cleanup
```

核心职责冻结：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，WorkflowRuntime 负责“如何执行节点”。**

## Worker Recovery Boundary

当 Worker 已成功 claim 一个 `pending Execution`，且发现该 Execution 下存在遗留 `running Node` 时：

```text
pending + running Node
        ↓
WORKER_RECOVERY_INTERRUPTED
        ↓
running → failed
        ↓
既有 failed → running 合法入口
        ↓
WorkflowRuntime retry policy
```

`running → running` 继续是非法状态转换。禁止通过放宽状态机、数据库 reset、降低 polling 频率等方式掩盖问题。

当前阶段不实现 `running Execution` checkpoint/resume；该能力属于后续 durable execution 需求。

## 开发者本轮实际验收结果

### 1. Worker targeted Unit

开发者最新反馈：

```text
uv run pytest -q tests/unit/test_workflow_worker.py tests/unit/test_workflow_execution_worker_fencing.py
9 passed in 1.09s
```

### 2. Migration

历史实际结果：

```text
0031_usage_provider_lifecycle (head)
```

### 3. Backend Regression

开发者最新反馈：

```text
413 passed, 3 skipped, 36 deselected in 30.47s
```

但同一次 Gate 的 Tenant Safe Real API 仍出现 1 个失败：

```text
test_circuit_breaker_half_open_probe_recovers_and_closes
POST /workflows/executions/{id}/run
→ 409 只有 pending Execution 可以 Run
```

分析结论：这是独立 Worker 在 Execution 创建后先行 claim 导致的合法 pending → Worker ownership 竞态，与此前已经记录的 Real API claim race 属于同一边界；生产 `/run` Contract 不应修改。

本轮测试整改：Circuit Breaker probe 改用既有 `run_or_observe_execution()` helper，真实调用 `/run`，遇到合法 `409 只有 pending Execution 可以 Run` 后继续通过真实 HTTP 查询 PostgreSQL 持久化终态，不产生第二个 Runtime。

因此：**代码整改已提交；等待开发者重新执行 Tenant Safe Real API / Backend Regression Gate 后更新最终验收结论。**

## 当前剩余工作

1. 拉取本轮最新 main；
2. 执行 Worker targeted tests；
3. 执行 Tenant Safe Real API Gate，确认 Circuit Breaker probe 竞态测试整改有效；
4. 执行 Backend Regression Gate；
5. 执行只读 Worker Runtime consistency diagnostic；
6. 执行 Scheduler / Worker Recovery Acceptance；
7. 根据实际反馈更新 Phase 2.5 Acceptance 和 Project Status。

## 当前禁止事项

- 禁止把 `running → running` 改成合法状态转换。
- 禁止通过自动 reset 数据库来掩盖 Worker 恢复问题。
- 禁止新增平行 Workflow Runtime 或第二套 Provider。
- 禁止用 GitHub Actions 结果替代开发者本地实际测试结果。
- 禁止让 Real API Gate 自动启动、停止或重启 API / Scheduler / Worker。
