# 2026-08-27 Durable Frontier Identity Canonicalization

## 1. 问题

`WorkflowFrontierIdentity` 的 `key()` 原实现直接拼接 `node_ids`。对于同一个 Execution、Workflow Version、Decision fingerprint 和同一组并行 Node，如果 Planner / Resume 在重建过程中产生不同遍历顺序，会得到不同 SHA-256 identity。

这会破坏 `enqueue_frontier()` 依赖 identity key 做的 Durable Frontier 幂等收敛，使逻辑上相同的并行 Frontier 可能形成两条持久化记录。

## 2. 根因

原 Contract 同时把两个不同概念放在了同一个字段上：

- `node_ids` 的原始顺序：属于 Runtime / Executor 的执行输入；
- Frontier identity：只需要表达同一个并行 Node 集合是否是同一个 Durable Frontier。

原 key 计算没有区分这两个语义。

## 3. 修复

`WorkflowFrontierIdentity.key()` 现在只在生成 identity key 时对 `node_ids` 做规范化排序：

```text
[node-c, node-a, node-b]
        ↓
[node-a, node-b, node-c]
        ↓
SHA-256 identity
```

实际 `WorkflowFrontierIdentity.node_ids` 不被修改，因此不会改变 Executor 的实际节点顺序。

identity 仍然同时包含：

- `execution_id`
- `workflow_version_id`
- `decision_fingerprint`
- canonical Node 集合

因此不会跨 Execution、Workflow Version 或 Decision 错误合并 Frontier。

## 4. 单元测试

新增：

```text
backend/tests/unit/test_frontier_identity.py
```

覆盖：

1. 相同并行 Node 集合不同顺序 → identity 相同；
2. Execution 不同 → identity 不同；
3. Workflow Version 不同 → identity 不同；
4. Decision fingerprint 不同 → identity 不同。

本轮未执行 pytest，未记录测试 PASS。

## 5. 后续边界

本修复只解决 Frontier identity 的确定性，不负责：

- DAG Planner 的节点选择；
- Runtime 执行顺序；
- Frontier Repository 的数据库唯一约束；
- Execution terminalization；
- Worker fencing。

这些能力继续由现有正式领域入口负责，避免产生第二套 Frontier identity / Planner / Runtime 实现。
