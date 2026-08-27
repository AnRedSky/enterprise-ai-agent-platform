# Durable Frontier Replay Execution 锁缺口

## 问题

`_resolve_completed_frontier_idempotency()` 原先锁定 source Frontier 后读取关联 `WorkflowExecution`，但没有在 Replay 幂等收敛路径锁定 Execution。

这使 Replay 在读取 `execution.status` 与并发 terminalization 之间存在观察窗口：Replay 可能基于旧 lifecycle 快照决定返回既有 Durable fact，而另一个事务同时改变 Execution lifecycle。

## 修复

Replay 收敛路径现在继续遵循统一的 `Frontier → Execution` 锁序：

```text
source Frontier FOR UPDATE
        ↓
completion fact 校验
        ↓
Execution FOR UPDATE
        ↓
Execution lifecycle 校验
        ↓
Replay convergence
```

这样 Replay 与正常 terminalization 使用相同的 Execution 生命周期锁边界，避免基于过期 lifecycle 快照完成错误收敛。

## 影响范围

- `backend/app/services/workflow/frontier_progression.py`
- `_resolve_completed_frontier_idempotency()`

## 测试状态

本次仅实现代码修复；按照当前阶段策略未执行 pytest、Backend Regression、Real API 或 E2E。未执行结果不得标记为通过。
