# Phase 2.10-II — Enterprise Operations Console / Operator Governance

## 1. 目标

在 Phase 2.10-I 完成 Runtime Notification、Metrics、SLO、Audit 与统一 Runtime Acceptance 后，继续推进 LT-03 Enterprise Operations Console，将现有 Runtime、Workflow、Agent、Trigger 与 Audit 能力收敛为可治理的企业运维工作台。

本阶段不重新实现已经稳定的 Runtime Notification、Metrics、Telemetry、Provider 或 Workflow 状态机，而是围绕现有 Backend Contract 建立统一的运维操作边界、诊断关联和高风险操作保护。

## 2. 当前状态

**开发中。II-01 Backend Operator Action Governance 已完成本地反馈验证；II-02 Global Runtime Operations 已完成本地 Backend Unit / Real PostgreSQL 验证；II-03 Worker / Scheduler Diagnostics Backend 与 Frontend 第一切片已实现；II-04 Audit / Trace Correlation Backend 第一切片已实现；II-05 Controlled Batch Operations Backend 第一切片已实现并完成开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 验证；II-06 Runtime Audit Query Backend 第一切片已完成开发者本地 Unit / API Contract / Real PostgreSQL Acceptance，当前进入查询性能强化。**

## 3. 第一切片：Operator Action Governance

（既有内容保持不变，详见历史提交。）

## 4. 第二切片：II-02 Global Runtime Operations

（既有内容保持不变，详见历史提交。）

## 5. 第三切片：II-03 Worker / Scheduler Diagnostics

（既有内容保持不变，详见历史提交。）

## 6. 第四切片：II-04 Audit / Trace Correlation

（既有内容保持不变，详见历史提交。）

## 7. 第五切片：II-05 Controlled Batch Operations

已实现并完成本地反馈验收：

- `BatchOperatorActionService` 统一编排 tenant-scoped 批量 Operator Action；
- 单批次最多 100 个资源，禁止重复资源 ID；
- 高风险动作继续复用 `OperatorActionGovernanceService` 的确认、权限、状态和幂等规则；
- Retry / Trigger Invoke 从批次键稳定派生单项幂等键；
- 逐项返回 succeeded / rejected / failed，合法项目不因同批次其他项目拒绝而停止；
- 所有状态变更继续委托现有 Workflow Execution / Trigger Service；
- `/api/v1/runtime/operator-actions/batch` Contract、Unit、Real PostgreSQL Acceptance 已通过开发者本地反馈；
- Real Acceptance 清理遗漏 Integration Event 的 tenant 外键问题已修复并重新通过。

## 8. 第六切片：II-06 Runtime Audit Query Backend 第一切片

### 8.1 缺口分析

II-01 至 II-05 已建立统一 Operator Action、全局 Runtime 查询、Worker/Scheduler Diagnostics、Audit/Trace 深链和批量操作，但现有 `/api/v1/runtime/operations/audit` 只有 `limit` 查询：缺少数据库分页、动作/资源/结果过滤和时间窗口过滤，不适合企业运维场景下持续增长的审计事实查询。

该缺口不需要新增数据库事实，也不应复制 AuditLog / Operator Action 的生命周期。II-06 第一切片直接扩展现有 `RuntimeOperationsService` 对 `RuntimeOperationAudit` 的只读查询入口。

### 8.2 Backend Contract

新增：

`GET /api/v1/runtime/operations/audit/query`

参数：

- `page`：从 1 开始，默认 1；
- `page_size`：默认 50，最大 100；
- `action`：动作精确过滤；
- `resource_type`：资源类型精确过滤；
- `resource_id`：资源标识精确过滤；
- `outcome`：执行结果精确过滤；
- `since` / `until`：创建时间范围。

返回：

```json
{
  "items": [],
  "page": 1,
  "page_size": 50,
  "total": 0
}
```

### 8.3 设计边界

1. tenant scope 永远来自认证 Claims，不接受 `tenant_id` 查询参数。
2. 查询只读，不修改任何 Runtime Durable Fact。
3. 查询使用数据库 `COUNT + OFFSET/LIMIT`，禁止把全量审计记录加载进应用内分页。
4. 排序固定为 `created_at DESC, id DESC`，保证同一时间戳下结果稳定。
5. `since > until` 明确返回 422，不依赖数据库产生隐晦错误。
6. 第一切片只扩展已有 RuntimeOperationAudit 查询入口，不新增 Audit 存储或第二套审计规则。

### 8.4 测试

新增：

- `tests/unit/test_runtime_operations_audit_query.py`；
- `tests/api_contract/test_runtime_operations_audit_query_contract.py`；
- `scripts/test/phase-2.10/14_runtime_audit_query_unit_gate.ps1`；
- `scripts/test/phase-2.10/15_runtime_audit_query_real_gate.ps1`。

开发者本地反馈已确认 Unit / API Contract 6 passed、Real PostgreSQL Acceptance 1 passed；真实验收最初出现 `datetime.utcnow()` 弃用警告，已纳入错误记录并修复。

## 9. 第七切片：II-06 Runtime Audit Query 查询性能强化

### 9.1 目标

第一切片已经证明 tenant isolation、分页与运维过滤的业务语义正确，但查询随着审计事实增长会同时承担 tenant、resource、outcome 等组合过滤。第二切片不改变 API Contract，不复制查询规则，只补齐与现有查询路径一致的 PostgreSQL 复合索引。

### 9.2 Database Hardening

新增 Alembic migration：`0050_runtime_audit_query_indexes`，建立：

- `(tenant_id, resource_type, resource_id, created_at)`：支持资源维度精确过滤与稳定时间排序；
- `(tenant_id, outcome, created_at)`：支持结果过滤与时间范围查询；
- `(tenant_id, actor, created_at)`：为后续运维审计主体过滤及常见审计追踪查询预留稳定索引路径。

索引均以 `tenant_id` 为第一列，确保数据库优化路径与既有 tenant boundary 一致，不提供跨租户扫描入口。

### 9.3 Warning Hardening

真实 PostgreSQL Acceptance 中发现 `datetime.utcnow()` 已被 Python 新版本标记为弃用。测试夹具统一使用 `datetime.now(UTC).replace(tzinfo=None)`，保持现有 PostgreSQL `DateTime` 无时区字段兼容，同时显式表达 UTC 语义。

### 9.4 自动化 Gate

新增：

- `scripts/test/phase-2.10/16_runtime_audit_query_hardening_unit_gate.ps1`；
- `scripts/test/phase-2.10/17_runtime_audit_query_hardening_real_gate.ps1`。

Gate 只负责探测数据库、执行 migration 与测试，不自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；Acceptance 测试数据继续自动创建和清理，不要求人工填写 ID。

## 10. 完成判定

每个 Backend 切片至少满足：

- Backend Contract、Service 边界完成；
- tenant boundary 有 unit + API Contract 覆盖；
- 不产生重复生命周期或事实源；
- Backend Regression 通过；
- 需要数据库结构变化时完成 Alembic migration 与本地 head 验证；
- 范围需要时执行 Real PostgreSQL / Real API Acceptance；
- 所有实际发生的工程错误和警告均记录到 `docs/04-errors/`。
