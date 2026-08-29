"""Agent Delegation Claim 缺失 Durable Frontier 工程错误记录。"""

# ERR-0030 Delegation Claim 未接入 Durable Frontier Worker

## 1. 现象

Phase 2.8 B1/B2 的 Delegation Claim 会创建 `WorkflowExecution` 并绑定 `worker_execution_id`，但默认 Worker 已经切换为 Durable Frontier 唯一调度入口。原实现没有为 Delegation Worker Execution 创建 `WorkflowFrontier`，同时默认 Worker 没有发现 pending Delegation 的调度入口。因此直接调用 `execute_claimed_execution()` 的 Real Gate 可以通过，但独立 Worker 无法从 pending Delegation 开始执行。

## 2. 根因

Delegation API 创建的是 pending durable fact；B1 Claim 是一个可调用的领域入口，但没有进入默认 Worker 的 discovery path。原 Claim 还绕过了 Scheduler/普通 Workflow 的 Frontier 生成路径，没有产生 Delegation 专用 Durable Frontier。于是 Claim、Execution、Frontier、Worker dispatch 四层事实没有形成完整闭环。

## 3. 修复

默认 Durable Frontier Worker 现在在没有普通 Frontier 可消费时，会通过 `claim_one_pending_delegation()` 原子发现一个 pending Delegation，并复用 `claim_delegation()`。Claim 在同一事务中创建：

```text
pending Delegation
    ↓
Durable Frontier Worker discovery
    ↓
claim_delegation()
    ├── WorkflowExecution
    └── Durable Frontier(delegation.target)
            ↓
      Worker dispatch
            ↓
      AgentDelegationRuntimeBridge
            ↓
      既有 WorkflowRuntime
```

Frontier identity 的 fingerprint 同时绑定 Delegation 与 Worker Execution generation，避免同一 Delegation 的历史 generation 复用旧 work item。Claim、Execution、Frontier 与 Claim Audit/Trace 在同一事务提交。

## 4. 预防

- 异步领域能力必须同时定义 durable fact、work-item discovery 与 runtime execution 三层边界。
- Real Gate 不得只直接调用 Runtime；必须覆盖正式 Worker dispatch 入口。
- 新增 durable work item 时必须复用现有 Frontier repository、lease、retry 与 fencing，不得创建第二套队列状态机。
- 多 Worker 竞争必须通过 PostgreSQL 行锁与 lease/fencing 验证，而不是依赖进程内锁。

## 5. 验证边界

本修复新增 B6 多 Worker Real Gate，使用两个独立 `WorkflowWorker` 实例通过正式 `dispatch_once()` 从 pending Delegation 开始消费 Durable Frontier，并验证真实 PostgreSQL 终态闭环。代码变更提交时尚未由本执行环境实际运行本地 Gate；因此不得预填 B6 Passed。
