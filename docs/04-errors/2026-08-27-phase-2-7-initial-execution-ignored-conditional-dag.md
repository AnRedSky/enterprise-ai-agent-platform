# Phase 2.7-A：Durable Resume completed Node 查询缺少显式 tenant scope

## 1. 发现

在继续 Phase 2.7-A Durable Recovery 一致性加固时发现，`WorkflowRuntime._load_completed_resume_nodes()` 原先只按当前 Execution 与 Resume Source 的 `execution_id` 读取 `WorkflowNodeExecution`，没有在查询层显式限制 `tenant_id`。

虽然正常调用链已经从 tenant-scoped Execution 进入 Runtime，但 Durable Recovery 的完成事实属于租户隔离的数据资产，查询本身必须形成完整的防御式边界，不能依赖所有上游调用者永远正确。

## 2. 影响

- 内部错误调用可能把其他租户的 NodeExecution fact 带入 DAG frontier 重建；
- Conditional Decision / Join state 的恢复可信边界依赖上游对象而不是查询自身；
- 不符合项目多租户 Runtime 的防御式 tenant boundary 要求。

## 3. 根因

`_load_completed_resume_nodes()` 的查询条件只有：

```text
execution_id IN (current_execution, resume_source)
status = completed
```

缺少：

```text
tenant_id = current_execution.tenant_id
```

## 4. 修复

- 在 `WorkflowNodeExecution` 查询中增加强制 `tenant_id` predicate；
- 保留 current Execution + Resume Source 的明确 execution scope；
- 不改变 Planner / Runtime / State Merge 的职责边界；
- 增加 Unit Test 验证 tenant scope 与 Execution scope。

## 5. 验证

新增：

```text
backend/tests/unit/test_workflow_dag_runtime_initialization.py
```

覆盖：

- 查询包含 `tenant_id` 条件；
- 查询只读取 current / source Execution；
- 多 root Branch state 仍保持独立快照。

当前环境未实际执行 pytest，因此测试状态只能记录为“待开发者本地执行”，不得记录 PASS。
