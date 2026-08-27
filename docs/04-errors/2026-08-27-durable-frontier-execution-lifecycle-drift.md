# Durable Frontier Execution Lifecycle Drift

## 问题

在 `complete_frontier_with_checkpoint()` 中，本次 progression 的目标状态由是否存在 `next_identity` 推导，但锁定关联 `WorkflowExecution` 后没有立即证明数据库中的当前 lifecycle 与目标一致。

这会留下旧 Frontier 面向 terminal Execution 继续写入 completion fact，或在非 running Execution 上创建 running completion 的风险。

## 根因

Frontier 是被消费的工作项，但 `WorkflowExecution.status` 才是 Execution 生命周期的权威 Durable fact。仅在进入函数前推导 `execution_status` 不足以证明数据库中的当前状态仍然匹配。

## 修复

在锁定 `WorkflowExecution` 后、任何 Frontier transition 或 Checkpoint 写入前增加 lifecycle equality guard：

```text
locked Execution.status == progression target
        ↓
允许继续

否则
        ↓
FrontierProgressionContractError
        ↓
Fail Closed
```

因此：

- 无 Next Frontier 时只能从 `running` Execution 收敛到 `completed`；
- 有 Next Frontier 时只能在 `running` Execution 上继续 progression；
- lifecycle drift 在 Frontier transition 之前被拒绝；
- 不新增 Execution / Frontier / Checkpoint；
- 继续沿用既有 Frontier → Execution 锁序与 owner / lease fencing。

## 单元测试

新增 `backend/tests/unit/test_frontier_progression_lifecycle.py`，覆盖：

1. terminal Execution + running target 拒绝；
2. running Execution + completed target 拒绝；
3. running Execution + terminal completion 正常进入 transition。

## 测试状态

本轮只实现 Unit Test，未执行 pytest、Backend Regression、Real API、E2E 或本地手动测试。不得记录为 PASS。

## 后续

继续执行 Phase 2.7 Success / Failure terminalization final audit 与 Replay convergence final audit；只有主线全部完成后才启动完整本地测试与验收流程。
