# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler restart acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**核心代码实现完成；Worker ownership fencing、orphaned running Node recovery、Scheduler/Worker Recovery Acceptance 已形成实现与验收闭环；当前继续进行 Worker lease ownership 边界硬化。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 已推进到 Worker lease heartbeat hardening：

```text
b6b6861 fix(worker): harden lease heartbeat recovery
```

随后本轮在该基线上继续完成 lease expiry ownership boundary 的代码与测试整改，并准备重新执行本地 Gate。

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
lease heartbeat（仅允许续未过期 lease）
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

## Worker Lease Ownership Boundary

本轮新增硬化规则：

```text
worker_owner == current worker
AND
worker_lease_expires_at > now
        ↓
允许 heartbeat 续租
```

lease 已过期时，即使数据库仍保留旧 `worker_owner`，旧 Worker 也不得自行复活 lease；heartbeat 必须退出，后续 Runtime 写入由 ownership fencing 保护。

该规则解决 lease 到期与 heartbeat 恢复之间的 ownership resurrection 窗口，不修改 Node 状态机，也不新增第二套 Runtime。

## 当前待本地验收工作

1. 拉取最新远端 `main`；
2. 执行 Worker targeted Unit，确认 recovery、ownership fencing、heartbeat retry 与 lease expiry case；
3. 执行 Tenant Safe Real API Gate；
4. 执行 Backend Regression Gate；
5. 执行只读 Worker Runtime consistency diagnostic；
6. 执行 Scheduler / Worker Recovery Acceptance；
7. 根据开发者实际结果更新 Phase 2.5 Acceptance 和 Project Status。

以上结果在开发者本地实际执行前，不记录为 Passed。

## 当前禁止事项

- 禁止把 `running → running` 改成合法状态转换。
- 禁止通过自动 reset 数据库来掩盖 Worker 恢复问题。
- 禁止新增平行 Workflow Runtime 或第二套 Provider。
- 禁止用 GitHub Actions 结果替代开发者本地实际测试结果。
- 禁止让 Real API Gate 自动启动、停止或重启 API / Scheduler / Worker。
- 禁止 lease 到期后旧 Worker 通过 heartbeat 自行复活 ownership。
