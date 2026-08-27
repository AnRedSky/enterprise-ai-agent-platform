# Phase 2.7-A：Join readiness 在 Branch Checkpoint 前被错误声明

## 1. 发现

继续推进 Durable Recovery Closure 时发现，`WorkflowDagMultiFrontierExecutor` 虽然定义了“Branch Checkpoint 成功后才能进入 Join readiness”的设计约束，但 `checkpoint_writer` 是可选参数。

在没有提供 Checkpoint writer 时，Executor 仍可能：

```text
Branch execute
    ↓
merged state
    ↓
join_ready = true
```

这会把进程内 Branch output 当成已经 durable 的事实。

## 2. 影响

- Worker 崩溃时，Join 可能建立在尚未持久化的 Branch output 上；
- Recovery 无法保证 Join 输入来自 durable Node facts；
- `join_ready` 与实际 Checkpoint 状态不一致；
- 违反 Phase 2.7-A 的 Durable Recovery source-of-truth 约束。

## 3. 修复

`WorkflowDagMultiFrontierExecutor.execute()` 现在将 Checkpoint callback 是否存在作为 readiness gate：

```text
Branch execute
      ↓
Checkpoint callback
      ↓ all frontier branches success
merged state
      ↓
join_ready = true
```

没有 writer 时：

```text
Branch results 可以返回
merged_state_data = None
join_ready = false
```

任一 Checkpoint callback 抛出异常时继续向上抛出，不生成 merged state，也不声明 Join ready。

## 4. 设计边界

Executor 仍然不直接访问数据库、不获取 Worker ownership、不实现 fencing 或 transaction。Checkpoint writer 必须由现有 WorkflowExecutionService / Checkpoint Service 在正式持久化边界中注入。

## 5. Unit Test

新增：

```text
backend/tests/unit/test_workflow_dag_executor_checkpoint_gate.py
```

覆盖：

- Multi-frontier 无 Checkpoint writer 时 `join_ready == false`；
- Multi-frontier 所有 Checkpoint 成功后才产生 merged state；
- 单 frontier 无 Checkpoint writer 时同样不能声明 Join ready。

当前环境未执行仓库本地 pytest，因此测试不得记录为 PASS。
