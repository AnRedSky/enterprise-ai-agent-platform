# Phase 2.7 DAG Runtime Sequence Contract 回归错误

## 发生时间

2026-08-27

## 范围

`WorkflowDagResumeRuntimeSequencePlanner`、DAG Resume Runtime Plan、Conditional Branching Decision metadata。

## 实际现象

本地执行 Phase 2.7 DAG 相关 Unit Test 时出现 3 个失败：

1. Branch frontier 测试期望 `多个 frontier`，但 Sequence Planner 先进入 Runtime Planner，因缺少 `branch_state_data` 提前失败。
2. 线性 DAG 的 `selected_predecessor_node_ids` 已由 Durable Decision Contract 明确保留 predecessor fact，但旧测试仍断言空元组。
3. Conditional Branching 选择 `yes` 后，Sequence Planner 继续循环并尝试把 `no` 作为下一步，导致条件分支被错误地线性展开。

## 根因

Sequence Planner 没有严格执行“先完成一次纯 Planner Decision，再把同一个 Decision 交给 Runtime”的边界，同时没有在条件分支 Decision 后停止顺序展开。

## 修复

- Sequence Planner 先调用 `WorkflowDagResumePlanner.plan()` 获取唯一 frontier Decision。
- 多 frontier 在进入 Runtime Planner 前立即 fail-closed，并返回稳定的 `多个 frontier` Contract 错误。
- 将同一个 `WorkflowDagResumePlan` 通过 `resume_plan` 传入 Runtime Planner，避免同一次 Runtime Resolution 重复计算 Decision。
- 条件边选中的首个 frontier 只交给当前顺序 Runtime，停止本次 Sequence Planner 的预展开，后续 Branch Node 由下一次 Durable Frontier 推进处理。
- 更新 metadata Unit Test，使其验证 `selected_predecessor_node_ids` 的 Durable predecessor fact。
- 新增可重复执行的 `backend/scripts/test/release/02_workflow_dag_resume_regression.ps1`。

## 验证状态

用户提供的修复前本地结果为 `30 passed, 3 failed`。

本次远端代码修复通过 GitHub Repository API 提交；当前会话无法在用户 Windows 本地环境执行 `uv run pytest`，因此修复后的测试结果不得标记为 PASS。用户必须按测试脚本在本地实际执行并反馈结果。
