# Phase 2.7-A Durable Frontier Contract

> 本文档记录 Phase 2.7-A Closure 后进入 Durable Frontier Scheduling 的首个生产交付单元。

## 1. 目标

将 Planner 产生的 frontier 从 Runtime 内存结果提升为具有稳定身份和有限生命周期的 Durable Scheduling Contract，为后续 Scheduler / Worker Claim 接入提供唯一领域入口。

## 2. Frontier Identity

```text
execution_id
+ workflow_version_id
+ decision_fingerprint
+ ordered frontier node ids
        ↓
SHA-256
        ↓
frontier:<digest>
```

Node 顺序必须保留 Planner 的确定性输出。不能把 frontier Node 集合无序化，否则会产生错误的重复 Frontier identity。

## 3. Lifecycle

```text
PENDING
   ↓ claim
CLAIMED
   ↓ start
RUNNING
   ├── success → COMPLETED
   ├── retry   → RETRY_WAIT → CLAIMED
   └── terminal failure → FAILED
```

`COMPLETED` 与 `FAILED` 都是终态，不允许重新 Claim。

## 4. 当前实现

- `backend/app/services/workflow/frontier.py` 提供唯一 Frontier Identity / lifecycle contract；
- 当前只实现纯领域规则，不直接访问 PostgreSQL、Scheduler 或 Worker；
- `backend/tests/unit/test_workflow_frontier.py` 覆盖 identity determinism、Planner Node 顺序和终态保护；
- 下一交付单元才增加 PostgreSQL Durable Frontier Record 与 Worker Claim；必须先增加 Alembic migration，再接入 Repository / Scheduler。
