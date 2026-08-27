# Phase 2.7：顺序 Resume Plan 丢失 Durable Decision Metadata

- 日期：2026-08-27
- 阶段：Phase 2.7-A Conditional Branching / Durable Recovery Closure
- 类型：Recovery / Runtime consistency

## 问题

`WorkflowDagResumeRuntimeSequencePlanner` 调用统一 `WorkflowDagResumeRuntimePlanner` 后，只重新组装了 Node、frontier 和 state_data，丢弃了 Planner 生成的 `selected_predecessor_node_ids` 与 `decision_fingerprint`。

这会导致顺序 Runtime 与 Conditional Recovery 的 Decision identity 不一致，后续 Trace replay / idempotency 无法可靠复用同一 Decision metadata。

## 修复

顺序计划现在直接透传：

- `selected_predecessor_node_ids`
- `decision_fingerprint`

同时为顺序 Planner 增加 `state_data_by_node` 输入，以便条件边重新规划时使用已完成 Node 的持久化状态，而不是依赖第二套条件判断逻辑。

## 设计边界

- Sequence Planner 仍然只负责纯内存规划；
- 不读取数据库；
- 不执行 Node；
- 不修改 Checkpoint；
- 不创建第二套 DAG Planner；
- Durable facts 仍由 PostgreSQL Node Execution / Checkpoint 提供；
- Trace 仍然只是审计和 replay consistency metadata。

## 验证范围

新增独立 Unit Test 覆盖顺序计划的 fingerprint 与 selected predecessor 传递。当前按开发策略暂停 Full Regression / E2E / Real API Acceptance，未在当前 GitHub API 环境中执行 pytest，不将测试标记为 PASS。
