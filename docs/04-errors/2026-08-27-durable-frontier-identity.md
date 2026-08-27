# 2026-08-27 — Durable Frontier Identity / Lifecycle Contract

## 工程发现

Phase 2.7-A 已完成条件规划、Checkpoint、Resume、幂等和 Runtime transaction ownership 后，下一层调度不能直接把 Runtime 内存中的 `frontier_node_ids` 当作 Durable Scheduler work item。否则 Worker 重启后没有稳定的 Frontier identity，也无法安全判断重复 Claim。

## 修复 / 交付

新增 `WorkflowFrontierIdentity` 与 `WorkflowFrontierStatus`，形成唯一领域契约：

- identity 绑定 execution、workflow version、Decision fingerprint 和有序 frontier Node；
- identity 使用 SHA-256 形成稳定幂等 key；
- lifecycle 限定 `pending → claimed → running → completed/failed`；
- retry 只能进入 `retry_wait → claimed`；
- terminal state 禁止重新 Claim。

## 尚未宣称完成

本交付单元没有伪造 PostgreSQL Durable Frontier。数据库模型、Alembic migration、Repository、Scheduler Claim/Fencing 将作为下一原子交付单元实现，并按治理规则先 migration 后业务代码。

## 测试状态

仅新增 Unit Test Contract；本地 pytest 未执行，因此不得记录为 PASS。Full Regression、Real API、E2E 继续暂停。
