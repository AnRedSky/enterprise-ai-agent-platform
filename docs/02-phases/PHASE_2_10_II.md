# Phase 2.10-II — Enterprise Operations Console / Operator Governance

## 1. 目标

在 Phase 2.10-I 完成 Runtime Notification、Metrics、SLO、Audit 与统一 Runtime Acceptance 后，继续推进 LT-03 Enterprise Operations Console，将现有 Runtime、Workflow、Agent、Trigger 与 Audit 能力收敛为可治理的企业运维工作台。

本阶段不重新实现已经稳定的 Runtime Notification、Metrics、Telemetry、Provider 或 Workflow 状态机，而是围绕现有 Backend Contract 建立统一的运维操作边界、诊断关联和高风险操作保护。

## 2. 当前状态

**开发中。II-01 Backend Operator Action Governance 已完成本地反馈验证；II-02 Global Runtime Operations 已完成本地 Backend Unit / Real PostgreSQL 验证；II-03 Worker / Scheduler Diagnostics Backend 与 Frontend 第一切片已实现；II-04 Audit / Trace Correlation Backend 第一切片已实现；II-05 Controlled Batch Operations Backend 第一切片已实现并完成开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 验证；当前进入 II-06 Runtime Audit Query Backend 第一切片。**

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
- `scripts/test/phase-2.10/14_runtime_audit_query_unit_gate.ps1`。

最低验收：Unit + API Contract + Backend targeted regression。该切片不需要 Migration。

## 9. 完成判定

每个 Backend 切片至少满足：

- Backend Contract、Service 边界完成；
- tenant boundary 有 unit + API Contract 覆盖；
- 不产生重复生命周期或事实源；
- Backend Regression 通过；
- 需要数据库结构变化时完成 Alembic migration 与本地 head 验证；
- 范围需要时执行 Real PostgreSQL / Real API Acceptance。
