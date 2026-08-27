# Phase 2.6 Join Readiness Contract

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-27

## 1. 本轮目标

在 Multi-frontier Runtime 已经可以执行 Branch、通过 `transition_node()` 持久化 NodeExecution / Checkpoint 后，将“所有 Branch 完成”与“Join Node 可执行”正式分离，建立独立 Join Readiness Domain Contract。

## 2. 正式入口

```text
WorkflowDagJoinReadiness
WorkflowDagJoinReadinessService
```

模块位置：

```text
backend/app/services/workflow/checkpoint/recovery/dag_join.py
```

正式 Recovery package 已通过 `__init__.py` 暴露该入口，避免调用方形成平行 import 路径。

## 3. Readiness Contract

```text
completed_node_ids
        +
predecessor node_outputs
        ↓
WorkflowDagJoinReadinessService
        ↓
┌───────────────────────────────┐
│ 所有 predecessor 已 completed? │
└──────────────┬────────────────┘
               │
        no ────┴──── yes
        ↓             ↓
 ready=false     State Merge
                      ↓
             conflict ?
              ┌───────┴───────┐
             yes              no
              ↓                ↓
           reject       ready=true
                              ↓
                         state_data
```

### 安全规则

1. Join Node 必须存在；
2. Join Node 必须至少拥有一个 predecessor；
3. predecessor 未全部 completed 时，返回 `ready=False`，不得提前生成 Join state；
4. predecessor 全部 completed 后，必须存在每个 predecessor 的持久化 output state；
5. predecessor state 必须通过统一 `WorkflowDagBranchStateMergeService` 合并；
6. 同键不同值继续显式拒绝，禁止 last-write-wins；
7. Readiness Service 不读取数据库、不执行 Node、不修改 Execution、不获取 Worker ownership；
8. 真正的 Join Node 执行仍由 `WorkflowRuntime` + `WorkflowExecutionService.transition_node()` 完成；
9. `ready=True` 表示 Join 的输入事实完整且可安全合并，**不表示 Join Node 已执行**。

## 4. 与当前 Runtime 的边界

当前 Runtime 已完成：

```text
Branch A
Branch B
   ↓
transition_node()
   ↓
NodeExecution + Checkpoint
   ↓
recompute frontier
```

本轮新增的是：

```text
completed predecessor facts
        ↓
Join Readiness Contract
        ↓
Join input state
```

尚未在本轮把 `WorkflowRuntime` 内已有的 predecessor merge 逻辑全部替换为该正式入口；这是下一步接入任务。原因是必须先保持现有 Runtime 主线稳定，再一次性完成 Join 状态机接入，避免在同一变更中同时改变 Resume frontier、Node transition 和 Join persistence 三个事务边界。

## 5. 下一主线

```text
Join Readiness Service
        ↓
WorkflowRuntime Join Node path
        ↓
transition_node(join, running)
        ↓
execute Join
        ↓
transition_node(join, completed)
        ↓
Join Checkpoint
        ↓
recompute next frontier
```

必须保证：

- 同一 Join Node 在同一 Execution 中遵守 `(execution_id, node_id)` 唯一执行事实；
- Worker lease / fencing 仍由既有 Execution Service 负责；
- Join execution 失败不能伪造 next frontier；
- Join completed 后才能让其 downstream Node 进入 frontier；
- Resume 重试不能重复执行已经持久化 completed 的 Join；
- Join state 必须来自其 predecessor 的持久化 output，而不是来自上一次 Runtime 的临时内存对象。

## 6. Unit Test

新增：

```text
backend/tests/unit/test_workflow_dag_join.py
```

覆盖：

- predecessor 未全部完成 → `ready=False`；
- 所有 predecessor 完成 → 合并 state；
- predecessor state 冲突 → 显式拒绝；
- predecessor output 缺失 → 显式拒绝。

按照当前开发策略，完整 Backend Regression、Real API、E2E、Release Gate 暂停；本轮仅维护 Unit Test。测试只有在开发者实际执行后才能记录为通过，本轮未虚构执行结果。

## 7. 当前阶段结论

Join Readiness 已从 Runtime 内部的布尔语义推进为独立 Domain Contract，但 Phase 2.6 尚未 Closure。

剩余核心工作：

1. Runtime 接入 `WorkflowDagJoinReadinessService`；
2. Join Node 正式执行与 Checkpoint；
3. Join 幂等与 Resume fencing；
4. Join → next frontier；
5. Recovery observability 统一接入；
6. Real API + PostgreSQL + Worker 验证；
7. Phase 2.6 Closure。
