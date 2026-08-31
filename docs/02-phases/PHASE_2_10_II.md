# Phase 2.10-II — Enterprise Operations Console / Operator Governance

## 1. 目标

在 Phase 2.10-I 完成 Runtime Notification、Metrics、SLO、Audit 与统一 Runtime Acceptance 后，继续推进 LT-03 Enterprise Operations Console，将现有 Runtime、Workflow、Agent、Trigger 与 Audit 能力收敛为可治理的企业运维工作台。

本阶段不重新实现已经稳定的 Runtime Notification、Metrics、Telemetry、Provider 或 Workflow 状态机，而是围绕现有 Backend Contract 建立统一的运维操作边界、诊断关联和高风险操作保护。

## 2. 当前状态

**开发中。II-01 Backend Operator Action Governance、II-02 Global Runtime Operations、II-03 Worker / Scheduler Diagnostics Backend、II-04 Audit / Trace Correlation Backend、II-05 Controlled Batch Operations Backend、II-06 Runtime Audit Query Backend 第一切片与查询性能强化均已完成开发者本地反馈验收；II-07 Runtime Audit Query 运维主体过滤第一切片已完成，并继续进行主体 + 动作组合过滤硬化。Runtime Audit / Trace Correlation 响应 Contract 硬化已实现，等待开发者本地 Backend Gate 验收。**

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
- `(tenant_id, actor, created_at)`：为运维审计主体过滤及常见审计追踪查询提供稳定索引路径。

索引均以 `tenant_id` 为第一列，确保数据库优化路径与既有 tenant boundary 一致，不提供跨租户扫描入口。

### 9.3 Warning Hardening

真实 PostgreSQL Acceptance 中发现 `datetime.utcnow()` 已被 Python 新版本标记为弃用。测试夹具统一使用 `datetime.now(UTC).replace(tzinfo=None)`，保持现有 PostgreSQL `DateTime` 无时区字段兼容，同时显式表达 UTC 语义。

### 9.4 自动化 Gate

新增：

- `scripts/test/phase-2.10/16_runtime_audit_query_hardening_unit_gate.ps1`；
- `scripts/test/phase-2.10/17_runtime_audit_query_hardening_real_gate.ps1`。

Gate 只负责探测数据库、执行 migration 与测试，不自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；Acceptance 测试数据继续自动创建和清理，不要求人工填写 ID。

## 10. 第八切片：II-07 Runtime Audit Query 运维主体过滤

### 10.1 第一切片：actor 精确过滤

已完成并通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance：

- 在既有 `RuntimeOperationsService.audit_query` 增加 `actor` 精确过滤；
- API 增加可选 `actor` 查询参数，最大长度 128；
- tenant scope 仍完全来自认证 Claims，不接受 `tenant_id` 查询参数；
- 复用 `0050_runtime_audit_query_indexes` 的 `(tenant_id, actor, created_at)` 索引；
- Acceptance 自动创建两个租户、不同 actor 与审计事实，验证 actor 过滤不会削弱 tenant isolation；
- Gate 不自动启动或停止任何服务。

### 10.2 当前后续硬化：actor + action 组合过滤

审计排障的常见场景是回答“**哪个主体执行了什么运维动作**”。现有查询已经允许多个精确条件叠加，但缺少针对 `tenant_id + actor + action + created_at` 的专用数据库访问路径，因此继续补齐组合索引，而不新增第二套查询入口。

新增 Alembic migration：`0051_runtime_audit_actor_action_index`，建立：

- `(tenant_id, actor, action, created_at)`：支持主体 + 动作精确过滤、时间窗口与稳定时间排序。

同时补充：

- Unit：验证 actor 与 action 条件同时进入既有 tenant-scoped 查询；
- Real PostgreSQL Acceptance：验证主体 + 动作组合过滤结果准确，并验证另一租户即使使用相同 actor/action 也不可被当前租户读取；
- `20_runtime_audit_actor_action_hardening_gate.ps1`：执行 head、`alembic upgrade head`、Unit/API Contract、Real PostgreSQL Acceptance；
- 不自动启动 API、Scheduler、Worker、PostgreSQL、Redis，不要求人工填写测试 ID。

### 10.3 设计边界

1. `actor` 仍为精确匹配，不引入模糊搜索或第二套主体解析规则。
2. `action` 继续复用既有精确过滤语义。
3. 所有查询条件始终叠加认证 tenant scope。
4. 新索引只优化既有查询，不改变审计事实生命周期，不改变 API 返回 Contract。
5. 不为单一字段组合无限制增加索引；当前索引只覆盖已验证的主体 + 动作运维查询场景。

## 11. 第九切片：Runtime Audit / Trace Correlation 响应 Contract 硬化

### 11.1 问题

既有双向关联 API 已经具备 tenant-scoped Execution / Trace / Audit / Operator Action 查询能力，但 `RuntimeCorrelationPageWithItems.items` 使用 `list[Any]`，导致 OpenAPI 无法明确表达 Trace 与 Audit 集合元素类型，也无法对错误领域对象形成公共 API 响应约束。

同时 `/traces/{trace_id}` 路径参数缺少显式长度边界，和其他 Runtime 运维 Contract 的输入约束不一致。

### 11.2 修复

- 新增 `RuntimeCorrelationTracePage`，明确 `items: list[WorkflowTraceItem]`；
- 新增 `RuntimeCorrelationAuditPage`，明确 `items: list[AuditLogItem]`；
- `RuntimeCorrelationResponse` 改用两个具体分页 Contract；
- `trace_id` 增加 `1..128` 路径参数边界；
- 不改变查询语义、tenant boundary 或数据存储。

### 11.3 自动化 Gate

新增：

- `tests/api_contract/test_runtime_correlations_contract.py`；
- `scripts/test/phase-2.10/23_runtime_correlation_contract_hardening_gate.ps1`。

Gate 执行 Runtime correlation Unit、API Contract 与 Backend targeted regression，并明确输出 Service startup boundary；禁止自动启动、重启或停止任何 API、Scheduler、Worker、PostgreSQL、Redis，不要求人工填写测试 ID。

## 12. 完成判定

每个 Backend 切片至少满足：

- Backend Contract、Service 边界完成；
- tenant boundary 有 unit + API Contract 覆盖；
- 不产生重复生命周期或事实源；
- Backend Regression 通过；
- 需要数据库结构变化时完成 Alembic migration 与本地 head 验证；
- 范围需要时执行 Real PostgreSQL / Real API Acceptance；
- 所有实际发生的工程错误和警告均记录到 `docs/04-errors/`。
