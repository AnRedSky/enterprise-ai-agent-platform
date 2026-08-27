# Phase 2.6 Recovery Policy / Automatic Recovery Addendum

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-27
>
> 本文件是 `PHASE_2_6.md` 的自动恢复实现补充记录；阶段总体状态仍以 `docs/PROJECT_STATUS.md` 与对应 Acceptance 文档为准。

## 1. 当前目标

将 Durable Resume 从人工 HTTP Resume 推进到可观测、可策略控制、可由 Scheduler 自动触发的恢复执行链，并安全支持 DAG 多 frontier Resume。

## 2. Recovery Policy / Domain

正式入口：

```text
WorkflowExecutionRecoveryPolicy
WorkflowExecutionRecoveryPolicyEvaluator
WorkflowExecutionAutomaticRecoveryService
WorkflowExecutionResumeContractService
```

默认策略：

```text
max_attempts = 3
cooldown_seconds = 60
```

Recovery Domain 负责 Candidate + Policy + Resume Contract；Scheduler 不复制这些业务规则，Worker 不直接启动恢复 Runtime。

## 3. Scheduler Recovery Scan

正式入口：

```text
WorkflowRecoveryScheduler.scan_once()
WorkflowRecoveryScheduler.run_forever()
```

Scheduler 只负责：

```text
发现 failed + worker_owner IS NULL
        ↓
Recovery Domain
        ↓
Resume Outcome Contract
   ┌────┴────────────┐
   ↓                 ↓
created       idempotency_hit
   └────┬────────────┘
        ↓
pending Resume Execution
        ↓
标准 Worker claim
```

每个候选使用独立 DB Session。Resume Contract 首先锁定 Source Execution 并检查确定性幂等键，然后委托既有 `WorkflowExecutionService.resume_from_latest_checkpoint()` 执行真正创建；数据库唯一约束继续作为最终安全兜底。

## 4. Recovery Outcome Contract

正式 outcome：

```text
rejected
created
idempotency_hit
```

Scheduler 只消费 Domain 返回的正式 outcome，不根据异常类型猜测竞争类型。

## 5. DAG Branch State Merge Contract

正式入口：

```text
WorkflowDagBranchState
WorkflowDagStateMergePlan
WorkflowDagBranchStateMergeService
```

规则：

```text
Branch A ──┐
Branch B ──┼──→ deterministic merge
Branch N ──┘

same key + same value       → merge
same key + different value → reject
```

禁止 `last-write-wins`。Merge 只处理顶层状态键；嵌套对象、列表追加及业务语义冲突必须由未来 Join / Conflict Contract 明确规定。

## 6. Multi-frontier Runtime Plan

正式入口：

```text
WorkflowDagResumeRuntimePlanner
WorkflowDagResumeRuntimePlan
```

Runtime Planner 已从“多 frontier 直接拒绝”推进为“显式生成多 Node frontier Plan”：

```text
WorkflowDagResumePlanner
        ↓
frontier = [A, B, ...]
        ↓
branch_state_data = {
    A: checkpoint_state_A,
    B: checkpoint_state_B,
}
        ↓
WorkflowDagBranchStateMergeService
        ↓
WorkflowDagResumeRuntimePlan
    ├── frontier_node_ids
    ├── nodes
    └── merged state_data
```

安全约束：

1. 多 frontier 必须为每个 frontier 提供已验证的分支 Checkpoint 状态；
2. 缺失 frontier 分支状态直接拒绝；
3. 非 frontier 分支状态直接拒绝；
4. 冲突顶层状态键直接拒绝；
5. Merge Result 和 Node Definition 均为深拷贝；
6. 单 frontier 继续兼容旧 `state_data` 参数；
7. 多 frontier 不提供 `frontier_node_id` / `node` 的隐式单 Node 选择；
8. 当前只完成 Runtime Plan，尚未宣称并行 Node 实际执行、Join readiness、Checkpoint frontier persistence 已完成。

## 7. Recovery Observability Contract

正式入口：

```text
WorkflowRecoveryEvent
WorkflowRecoveryEventLogger
```

事件：

```text
workflow.recovery.attempt
workflow.recovery.scan.completed
```

单次 Attempt 携带：

```text
execution_id
resume_execution_id
outcome
reason_code
attempt_count
max_attempts
occurred_at
```

事件模型禁止写入 Checkpoint `state_data`、Secret、Provider credential 和完整业务 payload。

后续 Metrics / Trace 接入必须复用该事件 Contract，不建立平行 Recovery 日志字段体系。

## 8. 单元测试

覆盖：

```text
backend/tests/unit/test_workflow_recovery_policy.py
backend/tests/unit/test_workflow_automatic_recovery_service.py
backend/tests/unit/test_workflow_resume_contract.py
backend/tests/unit/test_workflow_recovery_scheduler.py
backend/tests/unit/test_workflow_recovery_observability.py
backend/tests/unit/test_workflow_dag_state_merge.py
backend/tests/unit/test_workflow_dag_runtime.py
```

本轮新增覆盖：

- 多 frontier Runtime Plan；
- frontier Node 确定性排序；
- Branch State Merge 接入；
- 缺失 / 非 frontier branch state 拒绝；
- branch state 冲突拒绝；
- 单 frontier API 兼容；
- 多 frontier 禁止隐式选择单 Node。

当前环境未实际执行新增测试，因此不得记录为“已通过”。

## 9. 下一任务

1. 将 Multi-frontier Runtime Plan 接入真实 WorkflowRuntime / Worker；
2. 定义 branch execution 与 Join readiness；
3. 持久化 frontier / branch execution Checkpoint 事实；
4. 将 Recovery Event Contract 接入项目已有统一 observability / trace 基础设施；若当前没有统一基础设施，保持领域事件出口，不新增平行 exporter；
5. 增加自动恢复 Real HTTP + PostgreSQL + 独立 Worker 测试入口，但不作为当前主线阻塞项；
6. 完成 Phase 2.6 Closure 后进入下一阶段主线能力。