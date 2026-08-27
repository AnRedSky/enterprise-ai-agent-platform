# Phase 2.6 — Multi-frontier Branch Checkpoint Boundary

> 状态：开发中  
> 基线：`main`  
> 当前任务：Branch Execution → Branch Checkpoint → Join readiness

## 1. 本轮完成

在 `WorkflowDagMultiFrontierExecutor` 中正式增加 `BranchCheckpointWriter` callback：

```text
WorkflowDagResumeRuntimePlan
        ↓
Branch A execute
        ↓
Branch A checkpoint
        ↓
Branch B execute
        ↓
Branch B checkpoint
        ↓
all branches checkpointed
        ↓
Branch State Merge
        ↓
join_ready = true
```

该边界解决此前 Multi-frontier Coordinator 只有内存执行结果、但没有明确 Branch Checkpoint 持久化时序的问题。

## 2. 强制顺序

对每一个 frontier Branch：

```text
execute
  ↓
validate output is dict
  ↓
checkpoint_writer(node_id, state)
  ↓
next branch
```

因此：

- Branch Checkpoint 失败时，后续 Branch 不继续执行；
- Branch Checkpoint 失败时，Join 不得就绪；
- 所有 Branch Checkpoint 成功以后才能执行最终 State Merge；
- State Merge 冲突仍然显式失败；
- Executor 不捕获 Branch / Checkpoint 异常，由 Worker / WorkflowExecutionService 统一进行失败状态转换。

## 3. Persistence Boundary

`WorkflowDagMultiFrontierExecutor` **不直接操作 ORM / AsyncSession / DB transaction**。

实际生产 callback 必须由：

```text
WorkflowExecutionService
        ↓
Worker ownership + lease + fencing
        ↓
Node transition
        ↓
Checkpoint Service
        ↓
同一事务
```

提供。

这样不会绕过当前 `transition_node()` 的 ownership fencing 与 NodeExecution / Checkpoint 同事务规则。

## 4. 当前仍未宣称完成的内容

本轮只建立了正确的持久化边界，尚未伪装成真实 DB 接入完成：

```text
▶ WorkflowRuntime Resume path 接入
▶ WorkflowExecutionService.run() 接入 Branch Executor
▶ 每个 Branch 的真实 NodeExecution / Checkpoint ORM 写入
▶ DAG predecessor completion fact
▶ Join readiness / next frontier
▶ Worker 多 frontier ownership 模型
```

尤其不能把 `checkpoint_writer` callback 的存在解释为数据库已经持久化 Branch Checkpoint；只有真实 WorkflowExecutionService callback 接入并通过 Unit Test 后才能改变状态。

## 5. Unit Test

新增覆盖：

- 每个 Branch 在 Join 前完成 Checkpoint callback；
- Branch Checkpoint failure 会阻止后续 Branch；
- Branch Checkpoint failure 不允许 Join；
- 原有 Branch isolation / conflict / failure / missing state 继续覆盖。

当前没有执行完整测试流程；本轮仅保留 Unit Test。由于当前执行环境未实际运行 pytest，不记录虚假的“通过”结果。

## 6. 下一主线

下一步直接实现真实接入：

```text
WorkflowExecutionService.run()
        ↓
WorkflowRuntime Resume
        ↓
WorkflowDagResumeRuntimePlanner
        ↓
WorkflowDagMultiFrontierExecutor
        ↓
executor = real node execution
checkpoint_writer = real transition/checkpoint transaction
        ↓
DAG predecessor facts
        ↓
Join readiness
        ↓
next frontier
```

完成该闭环后，Phase 2.6 才进入最终 Closure Gate。