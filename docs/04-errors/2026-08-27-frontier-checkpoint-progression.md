# Durable Frontier → Checkpoint → Next Frontier

日期：2026-08-27

## 背景

Durable Frontier 已具备 identity、持久化、claim、lease fencing、expired recovery、Scheduler/Worker bridge 和 retry scheduling。下一风险是成功执行后出现部分提交：Checkpoint 已写入但 Frontier 未完成，或 Frontier 已完成但 Next Frontier 未入队。

## 实施

新增 `backend/app/services/workflow/frontier_progression.py`：

- `complete_frontier_with_checkpoint()` 在调用方事务中执行完整 progression；
- 首先通过 `worker_owner + attempt` 锁定并完成当前 Frontier，阻止 stale Worker 产生新 durable fact；
- 随后由 `WorkflowExecutionCheckpointService.append_next_in_transaction()` 锁定 Execution 并分配连续 Checkpoint sequence；
- Next Frontier 使用确定性 `WorkflowFrontierIdentity` 并通过已有 tenant/key unique constraint 幂等入队；
- Next Frontier 必须与当前 Frontier 属于同一 Execution / Workflow Version；
- Terminal Frontier 可只产生最终 Checkpoint，不创建后继 Frontier；
- Service 不执行 commit，任一阶段失败均由调用方 rollback。

## 锁顺序

统一为：

```text
Frontier → Execution/Checkpoint → Next Frontier
```

与现有 Worker Claim 保持一致，避免 Progression 与 Claim 形成反向锁等待链。

## 明确未做

Persistence 层不重新执行 DAG Planner、条件求值或 State Merge。`next_identity` 必须由上层唯一 Planner/Runtime 产生。下一任务是把该 primitive 接入真实 Runtime/DAG Planner success path。

## 测试

新增 `backend/tests/unit/test_frontier_progression.py`，覆盖 next frontier、terminal frontier、cross-execution rejection 和不 commit contract。本环境未实际执行 pytest，因此不记录 PASS。