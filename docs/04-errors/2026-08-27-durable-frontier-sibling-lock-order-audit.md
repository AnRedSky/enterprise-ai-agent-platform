# Durable Frontier sibling overlap 锁序审计

> 日期：2026-08-27
> 阶段：Phase 2.7 Durable Recovery / Replay Closure
> 状态：已修复

## 1. 问题

此前 `frontier_progression.py` 的 `_assert_next_frontier_has_no_active_node_overlap()` 在已经锁定当前 Frontier 与关联 Execution 后，又对同一 Execution 的活动 sibling Frontier 使用 `SELECT ... FOR UPDATE`。

这会形成：

```text
当前 progression
    Frontier
       ↓
    Execution
       ↓
    sibling Frontier
```

而 Claim / Recovery 等路径可能从某个 Frontier 开始再取得 Execution 锁，从而存在反向竞争窗口。

## 2. 修复

sibling overlap 查询改为普通一致性读取，不再锁 sibling Frontier。

该检查调用前已经由 progression 取得当前 Frontier 与关联 Execution 的 durable 锁，因此同一 Execution 的 ownership/progression 竞争被 Execution 锁串行化；继续锁 sibling Frontier 没有增加必要的 fencing 价值，反而扩大锁图。

核心原则：

```text
Frontier → Execution
      ↓
普通读取 sibling Frontiers
      ↓
Node-set overlap 判断
```

禁止形成：

```text
Execution → sibling Frontier
```

的额外锁序。

## 3. 验证实现

新增：

```text
backend/tests/unit/test_frontier_lock_order.py
```

测试直接检查 SQLAlchemy Select 的 `_for_update_arg` 为 `None`，确保未来修改不会重新引入 sibling 行锁。

## 4. 测试状态

本轮仅实现 Unit Test，未执行 pytest、Integration、Real API、E2E 或本地手动测试；不得记录 PASS。
