# Phase 2.7-A：首次执行未使用 Conditional DAG Planner

## 1. 发现

在继续 Phase 2.7-A Runtime Integration 时发现，`WorkflowRuntime.execute()` 原先只有 Durable Resume 路径使用 `WorkflowDagResumePlanner`。首次执行仍按 `definition.nodes` 数组顺序逐个执行，因此同一个带 `condition/default` 的 Workflow Version 在首次执行与 Resume 时存在两套不同的边语义。

## 2. 影响

- Conditional Branching 只在 Resume 场景生效；
- 首次执行可能执行本应未命中的分支；
- Join state 可能把静态 predecessor 集合误认为实际选中的 predecessor；
- 与 Phase 2.7-A Contract 的“当前 Runtime state 选择后继边”语义不一致。

## 3. 根因

`WorkflowRuntime.execute()` 将 DAG Runtime Integration 限定在 `resume_of_execution_id` 非空场景；普通 Execution 直接遍历 `nodes`。同时 `_build_frontier_branch_states()` 原先按 Definition 中全部 predecessor 构造 state，没有优先消费 Planner 输出的 selected predecessor facts。

## 4. 修复

- 新增统一 `_resolve_dag_context()`，首次执行和 Resume 均通过现有 `WorkflowDagResumePlanner` / `WorkflowDagResumeRuntimePlanner`；
- 保留无 `edges` 历史 Workflow 的顺序执行兼容语义；
- `_build_frontier_branch_states()` 增加 `selected_predecessor_node_ids` 输入；
- Conditional Join 优先使用 Planner selected predecessor，未命中分支不会成为 Join state 输入；
- 不新增第二套 Planner / Runtime / State Merge。

## 5. 验证

本轮新增 Unit Test 覆盖首次 DAG context 与 Conditional Join selected predecessor。当前环境未实际执行 pytest，因此测试状态只能记录为“待开发者本地执行”，不得记录 PASS。
