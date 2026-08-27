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

现象：测试替换父类 `tick_once(now=None)` 后，子类使用 `super().tick_once(now=now)` 产生 `multiple values for argument 'now'`。

整改：trace wrapper 使用位置参数调用父类 `tick_once(now)`，保持替换/装饰场景下的参数绑定稳定。

### 2.4 Worker heartbeat 测试入口与 Durable Frontier 默认入口漂移

现象：基础 Worker heartbeat / dispatch 单元测试从 package-level `WorkflowWorker` 入口执行，而当前 package-level 默认入口已经是 PlannerDriven Durable Frontier Worker；基础 Worker heartbeat contract 因此不再存在于该入口。

整改：基础 Worker 测试改为直接验证 `app.services.workflow_worker.runtime.WorkflowWorker`；package-level Worker 入口测试明确验证 PlannerDriven Durable Frontier Worker。

### 2.5 Checkpoint boundary / fencing 测试 fixture 漂移

现象：Checkpoint `_build()` 已要求 `frontier_id`；fencing 校验已经要求有效 lease 时间，但旧测试 fixture 未提供。

整改：测试显式提供 `frontier_id`，fencing fixture 提供未来有效 lease。

### 2.6 Lease-loss telemetry

现象：Lease-aware Worker 在没有 Recovery trace 的情况下失去 Execution ownership 时，原 Worker Runtime 不会产生 finished telemetry。

整改：Lease-aware Worker 在明确 lease loss 时补充 `RECOVERY_WORKER_FINISHED`，结果固定为 `aborted / WORKER_LEASE_LOST`。

## 3. 尚未完成的真实本地复验

以下结果在当前对话环境中未重新执行，因此不得标记为 PASS：

- `uv run pytest -q`
- Backend Release / Regression Gate
- Real HTTP API Gate
- Frontend Gate
- Browser E2E

## 4. 后续整改重点

1. 重新执行本地 Unit Regression，确认上述 Runtime / Scheduler / Worker / Checkpoint 修复后的实际结果。
2. 对 Retry Budget Exhaustion 的 governance audit / trace 断言继续核对实际 Runtime 行为；若仍失败，补齐生产 Runtime 的 retry-exhausted durable governance fact，而不是放宽测试断言。
3. 继续处理剩余 Resume / Durable Frontier 测试中的 Contract 漂移，优先区分“生产实现缺陷”和“旧测试仍引用已关闭 Contract”。
4. Unit Regression 稳定后，再按 `DEVELOPMENT.md` 顺序执行 migration verification、Real API、Frontend 与 E2E Gate。
