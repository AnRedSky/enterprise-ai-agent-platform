# Phase 2.8 B6 默认 Worker 入口回归与 Delegation Runtime 路由错误

## 1. 发生时间

2026-08-29

## 2. 现象

开发者基于 `3f293aea` 执行 B6 Multi-Worker Runtime Gate 时，Backend default regression 出现 3 个失败：

- `test_default_worker_uses_planner_driven_durable_frontier_dispatch`
- `test_workflow_worker_uses_planner_driven_frontier_worker`
- `test_package_worker_is_durable_frontier_worker`

失败原因均为公开 `WorkflowWorker` 被指向 `DurableFrontierWorkflowWorker`，而当前测试与正式入口契约要求 `PlannerDrivenDurableFrontierWorkflowWorker`。

此前修复还暴露了第二层运行时问题：将默认入口切换到 `DurableFrontierWorkflowWorker` 后，B2/B6 Real Gate 能进入 canonical `runtime_entry`，但不能继续通过 Planner-driven 默认入口执行 Delegation；若恢复 Planner-driven 默认入口而不区分 Delegation Frontier，则会再次绕过 `AgentDelegationRuntimeBridge`，导致 Delegation Target Agent Runtime 使用父 Workflow 的普通节点执行路径。

开发者反馈中的 Real Gate 随后出现 Provider `503 Service Unavailable`，请求目标为本地 OpenAI-compatible endpoint。该现象与父 Workflow fixture 的执行路径被错误触发一致，说明默认 Worker 入口与 Delegation Runtime Entry 的职责边界必须同时修正，不能只修改导出别名。

## 3. 根因

### 3.1 默认 Worker 契约被错误改写

`backend/app/services/workflow_worker/__init__.py` 在 `d44d6b86` 将：

```python
WorkflowWorker = PlannerDrivenDurableFrontierWorkflowWorker
```

改为：

```python
WorkflowWorker = DurableFrontierWorkflowWorker
```

该修改与现有单元 Contract 不一致，也破坏了当前阶段要求的 Planner-driven 默认入口。

### 3.2 Planner-driven Worker 的 Delegation 路由缺失

`PlannerDrivenDurableFrontierWorkflowWorker.execute_frontier()` 原先直接使用父 `WorkflowVersion.definition` 执行 Planner/Node。Delegation Worker Execution 的正确入口实际上是 `runtime_entry.execute_claimed_execution()`，该入口负责：

- `AgentDelegationRuntimeBridge.load()`；
- 构造 Delegation 专用内存 Runtime Version；
- 复用 Target Agent published version 与 Model Profile；
- Delegation timeout；
- Worker generation fencing；
- Delegation completion/failure/timeout 独立终态事务。

因此，Planner-driven 默认 Worker 必须保留，但 Delegation Frontier 不能走普通 Planner execution path。

## 4. 修复

### 4.1 恢复正式默认入口

恢复：

```python
WorkflowWorker = PlannerDrivenDurableFrontierWorkflowWorker
```

并明确说明 Planner-driven Worker 继承唯一 Durable Frontier Worker 的 Claim、Lease 与 Runtime 能力，不建立第二套 Execution 状态机。

### 4.2 Delegation Frontier 路由到唯一 Runtime Entry

在 `PlannerDrivenDurableFrontierWorkflowWorker` 增加 Delegation Frontier 识别逻辑：通过 `AgentDelegation.worker_execution_id + tenant_id` 判断当前 Frontier 是否属于已 Claim Delegation。

Delegation Frontier 命中后调用父类 `DurableFrontierWorkflowWorker.execute_frontier()`，由父类进入唯一 `runtime_entry.execute_claimed_execution()`；普通 Workflow Frontier 继续使用 Planner-driven execution。

这样形成：

```text
WorkflowWorker
  └─ PlannerDrivenDurableFrontierWorkflowWorker
       ├─ 普通 Workflow Frontier → Planner / Checkpoint progression
       └─ Delegation Frontier → DurableFrontierWorkflowWorker
                              → runtime_entry.execute_claimed_execution
                              → AgentDelegationRuntimeBridge
```

两条路径共享同一个 Claim、Frontier、Lease、WorkflowRuntime 与状态模型，没有新增 Provider、Queue、Retry 或 Recovery 实现。

## 5. 验证结果

开发者已完成后续本地验证，B6 正式 Gate 已全部通过：

```text
Delegation Claim + Worker dispatch Unit/Contract
38 passed in 1.08s

Backend default regression
870 passed, 3 skipped, 52 deselected in 34.61s

Migration/head
0039_workflow_node_execution_tenant_trigger (head)

Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
5 passed in 7.48s

[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed.
```

同时已验证 Windows 外部 Worker/Scheduler 隔离检查能够阻止测试环境中的非项目消费者污染 Delegation；在无外部消费者条件下 Gate 正常通过。

## 6. 状态

**已修复并已验证。**

该错误不再构成 Phase 2.8 blocker。历史现象和根因仍保留用于追溯；当前完成度以最新 B6 Real Gate 实际通过结果为准。除非后续出现新的回归，不应重新引入旧的默认 Worker 入口替换方案。
