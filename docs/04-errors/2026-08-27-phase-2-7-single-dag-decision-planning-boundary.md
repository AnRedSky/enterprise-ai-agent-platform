# 2026-08-27 Phase 2.7 — Single DAG Decision Planning Boundary

## 问题

Conditional DAG Runtime 在一次 `_resolve_dag_context()` 中先调用 `WorkflowDagResumePlanner.plan()` 计算 Decision，随后又调用 `WorkflowDagResumeRuntimePlanner.plan()`，后者再次运行同一个 Planner。

虽然两次调用当前均为纯函数，但这会形成两个 Decision calculation boundary：未来任一 Planner 输入读取、规则扩展或状态归一化发生变化时，同一次 Runtime Resolution 可能出现两次独立计算，削弱“Planner 是唯一 Decision Source”以及 fingerprint / frontier / predecessor 必须来自同一个计算结果的约束。

## 修复

`WorkflowDagResumeRuntimePlanner.plan()` 新增可选 `resume_plan: WorkflowDagResumePlan`。

调用方已经完成 Planner 计算时直接消费该 immutable plan，不再次调用 Planner；同时校验 supplied plan 的 `completed_node_ids` 与当前 Runtime 输入一致，并继续验证 fingerprint、frontier Node 与状态边界。

正式路径现在为：

```text
Durable completed facts
        ↓
WorkflowDagResumePlanner.plan()
        ↓
WorkflowDagResumePlan
        ├── completed
        ├── frontier
        ├── selected predecessors
        └── decision fingerprint
        ↓
WorkflowDagResumeRuntimePlanner.plan(resume_plan=plan)
        ↓
Runtime Plan
```

因此一次 Runtime Resolution 只产生一个 Decision calculation result。

## 单元测试

新增 Runtime Planner Contract：传入 `resume_plan` 时 mock Planner，若再次计算立即失败；同时验证 Runtime Plan 完整继承 fingerprint、frontier 与 selected predecessor。

当前环境未执行 pytest，不记录为 PASS。

## 边界

- 不创建第二套 Planner；
- Runtime Planner 仍是纯内存转换层；
- 不读取数据库；
- 不创建 NodeExecution；
- 不写 Checkpoint；
- 不改变 Worker ownership；
- Decision 仍只由 `WorkflowDagResumePlanner` 计算。
