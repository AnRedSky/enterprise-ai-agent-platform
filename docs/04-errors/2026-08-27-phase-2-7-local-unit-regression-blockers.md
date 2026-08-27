# Phase 2.7 本地 Unit Regression Blockers（2026-08-27）

## 1. 背景

本记录对应 `main` 分支 Phase 2.7 主线完成后的本地 Unit Regression 反馈。测试结果来自开发者本地实际执行，不将 GitHub Actions 作为验收依据。

## 2. 已确认并已整改

### 2.1 普通 Execution 不应查询 Recovery Trace

现象：普通 Workflow Execution 的 Runtime 入口也执行 Recovery trace 查询；Unit Test 使用轻量 AsyncMock DB 时会把未配置的 `AsyncMock` 当作 trace_id，进一步进入 telemetry `asdict()`，最终表现为 Runtime 500。

整改：只有存在 `resume_of_execution_id` 的 Recovery Resume Execution 才查询 Recovery trace；普通 Execution 直接进入基础 Runtime。

### 2.2 DAG NodeExecution tenant 字段不存在

现象：Runtime 查询 `WorkflowNodeExecution.tenant_id`，但 NodeExecution ORM 没有该字段，导致 DAG 初始化直接 `AttributeError`。

整改：DAG Runtime 按当前 Execution / Resume Source 的 `execution_id` 查询完成事实。tenant boundary 由 Execution 身份确定，不再引用不存在的 NodeExecution tenant 字段。

### 2.3 Scheduler trace wrapper 的 `tick_once` 参数绑定

现象：测试替换父类 `tick_once(now=None)` 后，子类使用位置参数调用时仍可能把显式 `None` 作为额外参数传入替换函数，导致参数绑定异常。

整改：trace wrapper 在调用者未提供 `now` 时直接调用父类默认参数；显式提供时间时才使用关键字参数传递。

### 2.4 Worker heartbeat 测试入口与 Durable Frontier 默认入口漂移

现象：基础 Worker heartbeat / dispatch 单元测试从 package-level `WorkflowWorker` 入口执行，而当前 package-level 默认入口已经是 PlannerDriven Durable Frontier Worker；基础 Worker heartbeat contract 因此不再存在于该入口。

整改：基础 Worker 测试改为直接验证 `app.services.workflow_worker.runtime.WorkflowWorker`；package-level Worker 入口测试明确验证 PlannerDriven Durable Frontier Worker。

### 2.5 Checkpoint boundary / fencing 测试 fixture 漂移

现象：Checkpoint `_build()` 已要求 `frontier_id`；fencing 校验已经要求有效 lease 时间，但旧测试 fixture 未提供。

整改：测试显式提供 `frontier_id`，fencing fixture 提供未来有效 lease。

### 2.6 Lease-loss telemetry

现象：Lease-aware Worker 在没有 Recovery trace 的情况下失去 Execution ownership 时，原 Worker Runtime 不会产生 finished telemetry。

整改：Lease-aware Worker 在明确 lease loss 时补充 `RECOVERY_WORKER_FINISHED`，结果固定为 `aborted / WORKER_LEASE_LOST`。

## 3. 本轮新确认的阻塞

### 3.1 DAG Resume Runtime 完成事实顺序校验错误

现象：`WorkflowDagResumeRuntimePlanner` 将 `definition.nodes` 中的 Node 对象与 Planner 输出的 Node ID 元组直接比较，导致合法 Resume / Conditional / Multi-frontier 计划统一抛出 `resume_plan 与 completed_node_ids 不一致`。

整改：校验时先从 Definition Node 对象提取 `id`，再与 Planner 的有序 completed Node ID 元组比较；不改变 Planner 的确定性顺序契约。

### 3.2 Scheduler trace wrapper 对默认参数的兼容性

现象：测试通过替换父类 `tick_once(now=None)` 模拟 decorated / monkeypatched runtime 时，`super().tick_once(now)` 会把绑定后的 `self` 与显式 `None` 同时传入替换函数，形成参数数量错误。

整改：`now is None` 时调用 `super().tick_once()`；显式时间才调用 `super().tick_once(now=now)`。这样保留真实 Scheduler 的参数语义，也兼容无显式时间的包装场景。

### 3.3 Retry Exhaustion Governance 仍需继续复验

现象：当前 Unit Regression 中 Retry Budget / Workflow Deadline exhaustion 的 governance audit / trace 断言仍未观察到事件，说明当前 Durable Runtime 重构后的 Retry loop 与既有 governance Contract 之间存在回归或测试入口漂移。

处理策略：下一整改单元必须直接核对 `WorkflowRuntime._execute_node_with_policy` 的 retry exhaustion 分支与 `WorkflowExecutionService.run` 的 terminal convergence，不能通过放宽断言掩盖生产行为缺失。

## 4. 尚未完成的真实本地复验

以下结果在当前对话环境中未重新执行，因此不得标记为 PASS：

- `uv run pytest -q`
- Backend Release / Regression Gate
- Real HTTP API Gate
- Frontend Gate
- Browser E2E

## 5. 后续整改重点

1. 重新执行 DAG Runtime / Scheduler targeted Unit Test，确认本轮生产修复。
2. 继续恢复 Retry Budget / Workflow Deadline 的 durable governance fact。
3. 对剩余 Resume / Durable Frontier 测试逐项区分“生产实现缺陷”和“旧测试仍引用已关闭 Contract”。
4. Unit Regression 稳定后，再按 `DEVELOPMENT.md` 顺序执行 migration verification、Real API、Frontend 与 E2E Gate。
