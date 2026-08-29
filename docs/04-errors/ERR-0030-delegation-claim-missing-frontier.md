"""Agent Delegation Claim 缺失 Durable Frontier 工程错误记录。"""

# ERR-0030 Delegation Claim 创建 Execution 后未进入 Durable Frontier

## 1. 现象

Phase 2.8 B1/B2 的 Delegation Claim 会创建 `WorkflowExecution` 并绑定 `worker_execution_id`，但默认 Worker 已经切换为 Durable Frontier 唯一调度入口。原实现没有为 Delegation Worker Execution 创建 `WorkflowFrontier`，因此直接调用 `execute_claimed_execution()` 的 Real Gate 可以通过，但独立运行默认 `run_worker.py` 时该 Delegation 没有可消费的 durable work item。

## 2. 根因

Delegation Claim 复用了旧的 Workflow Execution ownership，但绕过了 Scheduler/普通 Workflow 的 Frontier 生成路径。B2 Runtime Bridge 只解决了“如何执行已 Claim Execution”，没有解决“默认 Frontier Worker 如何发现该 Execution”。这造成了 Claim、Execution 与 Worker dispatch 三层事实不完整闭环。

## 3. 修复

`claim_delegation()` 在创建 `WorkflowExecution` 后，同一事务显式调用 `enqueue_frontier()` 创建单 Node `delegation.target` Durable Frontier：

```text
Delegation Claim
    ↓
WorkflowExecution
    ↓
Durable Frontier(delegation.target)
    ↓
默认 Durable Frontier Worker
    ↓
AgentDelegationRuntimeBridge
    ↓
既有 WorkflowRuntime
```

Frontier identity 的 fingerprint 同时绑定 Delegation 与 Worker Execution generation，避免历史 generation 复用旧 work item。Claim、Execution、Frontier 与既有 Audit/Trace 在同一事务提交。

## 4. 预防

- Delegation 类似的异步执行入口必须同时回答“如何持久化”和“默认 Worker 如何发现”。
- Real Gate 不得只直接调用 Runtime；必须覆盖正式 Worker dispatch 入口。
- 新增 durable work item 时必须复用现有 Frontier repository、lease、retry 与 fencing，不得创建第二套队列状态机。

## 5. 验证边界

本修复新增 B6 多 Worker Real Gate，使用两个独立 `WorkflowWorker` 实例并通过真实 PostgreSQL Durable Frontier dispatch 完成 Delegation。代码变更提交时尚未由本执行环境实际运行本地 Gate；因此不得预填 B6 Passed。
