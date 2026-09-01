# 2026-09-01 Operator Audit 查询索引事实源偏移

## 1. 问题现象

Phase 2.10-II 已将 Operator Audit 查询统一收敛到 `AuditLog`，但既有 `0050_runtime_audit_query_indexes` migration 创建的复合索引仍针对历史 `runtime_operation_audits` 表。这样查询 Service 与数据库优化目标不一致，真实 Operator Audit 查询无法使用这组索引获得预期的 tenant-scoped 过滤优化。

## 2. 根因

`OperatorAuditQueryService` 已明确以 `audit_logs` 作为唯一 Operator Action 审计事实源，而 `0050_runtime_audit_query_indexes` 创建的是 `runtime_operation_audits` 的 `tenant + resource/outcome/actor` 索引。该 migration 属于历史 Runtime Operation Audit 模型，后续 Canonical Operator Audit 收敛后没有同步建立新的 `AuditLog` 查询索引。

这不是查询结果正确性错误，而是事实源收敛后留下的数据库性能与治理边界缺口。

## 3. 修复

新增 `0051_operator_audit_query_indexes`：

- `tenant_id + action + created_at`；
- `tenant_id + actor_id + created_at`；
- `tenant_id + resource_type + resource_id + created_at`；
- `tenant_id + workflow_execution_id + created_at`；
- `tenant_id + trace_id + created_at`。

所有索引均以 `tenant_id` 为首列，保证当前租户边界与常用精确过滤同时进入数据库查询路径。

## 4. 验证

新增 Real PostgreSQL Acceptance 验证索引实际存在于 `audit_logs`，并验证 tenant boundary 为复合索引首列。

Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\26_operator_audit_query_performance_gate.ps1
```

Gate 不自动启动任何 API、Scheduler、Worker、PostgreSQL 或 Redis 服务；PostgreSQL 不可用时仅输出标准人工启动命令并返回未执行状态。

## 5. 设计边界

`0050_runtime_audit_query_indexes` 不在本修复中回滚或删除，因为其可能已被历史数据库应用；本次只为当前 Canonical `AuditLog` 事实源建立新的正式索引，避免通过修改已执行 migration 破坏已有环境。
