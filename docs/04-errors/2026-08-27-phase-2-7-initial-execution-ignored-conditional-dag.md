# Phase 2.7-A：首次执行未使用 Conditional DAG Planner

## 1. 发现

在继续 Phase 2.7-A Runtime Integration 时发现，`WorkflowRuntime.execute()` 原先只有 Durable Resume 路径使用 `WorkflowDagResumePlanner`。首次执行仍按 `definition.nodes` 数组顺序逐个执行，因此同一个带 `condition/default` 的 Workflow Version 在首次执行与 Resume 时存在两套不同的边语义。

继续修复后又发现 `app/runtime/workflow/dag_runtime.py` 对基础 Runtime 的 `_build_frontier_branch_states()` 存在重复实现且参数契约不同：基础 Runtime 新增了 `definition` 与 `selected_predecessor_node_ids`，扩展 Runtime 仍保留旧签名，导致多态调用存在运行时参数不匹配风险。

此外，首次执行的 DAG 如果存在多个 root，不能因为没有 completed Node 就直接交给 Multi-frontier Runtime；每个 root 都必须先获得当前 Execution 的独立输入状态。

## 2. 影响

- Conditional Branching 只在 Resume 场景生效；
- 首次执行可能执行本应未命中的分支；
- Join state 可能把静态 predecessor 集合误认为实际选中的 predecessor；
- DAG Runtime 扩展与基础 Runtime 的方法签名不一致，存在运行时调用失败风险；
- 多 root 首次执行无法形成合法的 Multi-frontier branch state；
- 与 Phase 2.7-A Contract 的“当前 Runtime state 选择后继边”语义不一致。

## 3. 根因

`WorkflowRuntime.execute()` 将 DAG Runtime Integration 限定在 `resume_of_execution_id` 非空场景；普通 Execution 直接遍历 `nodes`。同时 `_build_frontier_branch_states()` 原先按 Definition 中全部 predecessor 构造 state，没有优先消费 Planner 输出的 selected predecessor facts。

后续扩展层为了实现 Join / Recovery Trace 保留了与基础 Runtime 重复的 DAG state / Resume 实现，没有同步基础方法签名；这违反“同一能力只保留一个正式实现入口”的治理要求。

## 4. 修复

- 首次执行和 Resume 均通过现有 `WorkflowDagResumePlanner` / `WorkflowDagResumeRuntimePlanner`；
- 首次执行存在多个 root 时，为每个 root 建立当前输入的独立 state 快照，再进入现有 Multi-frontier Runtime；
- 保留无 `edges` 历史 Workflow 的顺序执行兼容语义；
- 基础 Runtime 的 `_build_frontier_branch_states()` 统一负责 DAG predecessor state 构造，并消费 Planner selected predecessor facts；
- `app/runtime/workflow/dag_runtime.py` 删除重复的 `_build_frontier_branch_states()`、Resume context 等实现，只保留 Join Node、DAG Contract 校验、首次多 root 初始化与 Recovery Trace 扩展；
- 不新增第二套 DAG Planner / Runtime / State Merge。

## 5. 验证

新增 `backend/tests/unit/test_workflow_dag_runtime_initialization.py`，覆盖：

- 多 root 首次 DAG frontier；
- 每个 root 获得独立输入快照；
- Join Node 类型扩展不复制基础 Runtime 执行能力。

当前环境未实际执行 pytest，因此测试状态只能记录为“待开发者本地执行”，不得记录 PASS。
