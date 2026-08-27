# 2026-08-27 Durable Execution terminalization bypass

## 问题

`WorkflowExecutionService.transition()` 是通用 Execution 状态转换入口。修复前，它允许 `running → completed/failed` 直接修改 Execution，并没有证明同一 Execution 已经没有 `pending`、`retry_wait`、`claimed` 或 `running` Frontier。

因此可能形成：

```text
Execution = completed/failed
+
活动 Frontier 仍可被 Scheduler/Worker 消费
```

这会绕过 Phase 2.7 的 Frontier → Checkpoint → Next Frontier / terminal Execution Durable convergence contract。

## 修复

在 `transition()` 的 `completed` / `failed` 路径中，Execution 行锁定后增加统一活动 Frontier 查询；发现活动 Frontier 即返回 HTTP 409，不修改 terminal state。

`cancelled` 保持独立的 operator terminalization 语义，不受该业务约束。

## 验证实现

新增 Unit Test：

`backend/tests/unit/test_execution_terminalization_boundary.py`

覆盖活动 Frontier 拒绝和无活动 Frontier 放行两个边界。

## 测试状态

测试实现已提交，但本轮没有执行 pytest、Regression、API 或 E2E。任何测试 PASS 均不得在本轮记录。
