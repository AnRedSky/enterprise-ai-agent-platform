# Phase 2.7 Real API：Durable Frontier 重复 Checkpoint

## 1. 发现时间

2026-08-28

## 2. 现象

Tenant Safe Real API 中 Durable Resume / Resume DAG / Resume Failure 出现 Checkpoint 数量或 Node identity 与验收 Contract 不一致：

- Resume 线性链路出现额外 Checkpoint；
- Resume DAG 出现 `node_id=None` 的 `frontier_completed` Checkpoint 与 Node-level Checkpoint 混合；
- Resume failure-after-frontier 出现额外 Execution-level completion fact。

## 3. 根因

Durable Frontier Worker 通过 `WorkflowRuntime._execute_node_with_policy()` 执行 Node 时，既有 `WorkflowExecutionService.transition_node()` 会写入 `node.completed` Checkpoint；随后 Worker 又通过 `complete_frontier_with_checkpoint()` 写入正式的 `frontier_completed` Checkpoint。

因此同一个 Durable Frontier 同时产生 Node-level 与 Execution-level completion facts，破坏 Phase 2.7 所要求的单一 Frontier progression durable write boundary。

## 4. 修复原则

Durable Frontier Worker 已提供 Worker ownership / fencing 参数时，`node.completed` 不再由通用 Checkpoint Service 持久化；NodeExecution 状态事实仍正常持久化，正式恢复 Checkpoint 统一由 Frontier progression 写入 `frontier_completed`，并绑定 source Frontier。

普通 HTTP / 非 Durable Frontier 执行仍保留原有 Node-level Checkpoint 行为。

## 5. 验收要求

Resume Real API 应满足：

- Resume 每个已成功 Frontier 只产生一个 `frontier_completed` Checkpoint；
- `frontier_completed.node_id/node_status/node_attempt` 均为空；
- `frontier_completed.frontier_id` 必须存在；
- NodeExecution lineage 仍完整保存；
- 不产生重复 Node-level / Execution-level completion fact。

## 6. 状态

代码修复已提交到 `main`，等待开发者本地 Tenant Safe Real API 重新执行确认。不得在重新执行前标记 Phase 2.7 验收通过。
