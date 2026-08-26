# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler restart acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**核心代码实现完成；Worker ownership fencing、orphaned running Node recovery、Scheduler/Worker Recovery Acceptance 已形成实现与验收闭环；当前继续进行 heartbeat 首轮执行边界硬化。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 基线为：

```text
33530ff docs(status): align latest worker hardening baseline
```

本轮继续整改：

```text
fix(worker): run lease heartbeat ownership check immediately
 test(worker): cover immediate heartbeat ownership check
 docs(worker): record heartbeat first-tick regression
```

本轮问题来自开发者实际 Backend Regression 结果：heartbeat 首轮先等待完整 interval，导致 ownership 已失效时不能在测试门限内立即退出。整改只调整 heartbeat 调度顺序，不放宽 ownership fencing 或 Node 状态机。

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
lease heartbeat：首轮立即检查，后续周期续租
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

当前正式规则：

```text
heartbeat task 创建
      ↓
立即检查并续租
      ↓
worker_owner == current worker
AND
worker_lease_expires_at > now
      ↓
允许后续周期续租
```

lease 已过期时，即使数据库仍保留旧 `worker_owner`，旧 Worker 也不得自行复活 lease；heartbeat 必须退出，后续 Runtime 写入由 ownership fencing 保护。

本轮新增边界：heartbeat 首轮不能先等待 `lease_seconds / 3`。周期 interval 只用于成功续租后的下一轮调度；首轮立即检查 ownership，避免无意义的初始等待扩大 ownership 暴露窗口。

## 当前本地验收状态

开发者最新反馈：

```text
Worker targeted Unit: 10 passed in 1.18s
Backend Regression: 415 passed, 3 skipped, 36 deselected，失败于 test_lease_heartbeat_stops_when_ownership_is_lost
Tenant Safe Real API: 35 passed in 67.73s
Worker Runtime consistency: PASS，但存在历史 expired running lease warning
Scheduler / Worker Recovery Acceptance: 1 passed in 8.67s
```

Backend Regression 的 heartbeat 失败已完成代码级定位与整改，并新增首轮 heartbeat 防回归测试。**整改后的本地 Gate 尚未执行，因此当前不得标记 Backend Regression 为 Passed。**

## 当前禁止事项

- 禁止把 `running → running` 改成合法状态转换。
- 禁止通过自动 reset 数据库来掩盖 Worker 恢复问题。
- 禁止新增平行 Workflow Runtime 或第二套 Provider。
- 禁止用 GitHub Actions 结果替代开发者本地实际测试结果。
- 禁止让 Real API Gate 自动启动、停止或重启 API / Scheduler / Worker。
- 禁止 lease 到期后旧 Worker 通过 heartbeat 自行复活 ownership。
