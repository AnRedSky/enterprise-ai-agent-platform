# Phase 2.7 Final Convergence Audit

## 本轮主线收口：Execution terminalization 不得绕过 Frontier

### 发现

`WorkflowExecutionService.transition()` 是通用 Execution 状态入口，原实现允许 `running → completed/failed` 直接修改 Execution，即使同一 Execution 仍存在 `pending`、`retry_wait`、`claimed` 或 `running` Frontier。

这会形成：

```text
Execution = terminal
+
同一 Execution 仍存在可消费 Frontier
```

该状态与 Phase 2.7 的 Durable terminalization contract 冲突，因为旧 Frontier 仍可能被 Scheduler/Worker 消费，而 Execution 已经不可继续推进。

### 修复

`transition()` 在 `completed` / `failed` 前增加统一的活动 Frontier 检查：

```text
Execution FOR UPDATE
        ↓
状态转换合法性
        ↓
查询同 Execution 活动 Frontier
        ↓
存在活动 Frontier → HTTP 409 / rollback
        ↓
无活动 Frontier → 允许 terminalization
```

`cancelled` 不使用该约束，因为人工取消是独立的 operator terminalization 语义。

### 与 Frontier progression 的关系

正式的 Success terminalization 仍由 `complete_frontier_with_checkpoint()` 负责；本修复用于封住通用 Execution Service 的旁路，使所有 `completed/failed` Durable terminal state 都不能绕过 Frontier 收口规则。

### Unit Test

新增：

`backend/tests/unit/test_execution_terminalization_boundary.py`

覆盖：

1. 存在活动 Frontier → 拒绝 terminalization。
2. 不存在活动 Frontier → 允许继续。

### 测试状态

本轮只新增 Unit Test 实现，**没有执行 pytest**。不得将本轮标记为测试通过。

## 下一步

继续审计：

- Success terminalization 与 completion Checkpoint 的原子关系；
- Failure / retry exhaustion 与 Frontier 状态的最终收敛；
- Recovery / Replay 与 terminal Execution 的交叉路径；
- 所有 Execution terminal state 写入入口是否存在类似旁路。
