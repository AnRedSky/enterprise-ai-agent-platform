# Phase 2.10 — Enterprise Integration Event Operations

## 目标
在 Phase 2.9 已形成 Durable Integration Event → Reliable Delivery → Webhook → Replay/Audit 基础能力后，建设面向企业运维的统一事件操作面：查询、投递诊断、Replay、审计、指标、SLO 与死信治理。

## 2.10-II Backend Operator Governance / Audit

### II-01 ～ II-07
状态：**已完成 Backend 实现与开发者本地验证基线**。

- Operator Action Governance：统一操作定义、确认、幂等、状态可用性与生命周期委托；
- Global Runtime Operations、Worker / Scheduler Diagnostics、Audit / Trace Correlation、Controlled Batch Operations 已形成第一切片；
- Runtime Audit Query 已收敛到 `AuditLog` 唯一事实源，支持 tenant-scoped 分页、精确过滤、时间窗口及稳定响应 Contract；
- Runtime Audit / Trace Correlation 已支持正式 `workflow_execution_id` 优先及 tenant-scoped 历史 `trace_id` 恢复；
- Operator Audit Query API 已注册并限制为管理员访问；
- 开发者本地已反馈相关 Gate 修复通过，当前继续推进数据库查询路径与 Canonical AuditLog 事实源一致性。

### II-08 Canonical Operator Audit Query Performance / Fact-Source Alignment

状态：**代码与 Acceptance 已实现，等待开发者本地 Gate 实际执行**。

发现的真实缺口：现有 `0050_runtime_audit_query_indexes` 针对历史 `runtime_operation_audits` 建立索引，而当前 `OperatorAuditQueryService` 已统一以 `audit_logs` 为唯一 Operator Action 审计事实源。若不补齐当前事实源索引，查询 Contract 虽正确，但生产查询优化路径与 Canonical AuditLog 不一致。

本切片新增 `0051_operator_audit_query_indexes`：

- `tenant_id + action + created_at`；
- `tenant_id + actor_id + created_at`；
- `tenant_id + resource_type + resource_id + created_at`；
- `tenant_id + workflow_execution_id + created_at`；
- `tenant_id + trace_id + created_at`。

所有复合索引均以 `tenant_id` 为首列，保持数据库层与应用层 tenant boundary 一致。新增 Real PostgreSQL Acceptance 验证索引实际位于 `audit_logs`，不修改已经执行的 `0050` 历史 migration。

对应 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\26_operator_audit_query_performance_gate.ps1
```

## 2.10-I 当前进度

Phase 2.10-I 已完成 Runtime Notification Lifecycle、Worker tenant/consumer-group 隔离、Claim Competition、Retry/Lease、Dead Letter Replay、Fallback、SLO/Metrics、Runtime Audit、Integration Event 幂等与 Canonical Metrics Export Contract。

## 约束
- Operations API 不绕过 Repository 直接修改 Delivery 状态。
- 所有运维能力必须 tenant-scoped。
- Metrics 不建立平行业务事实源。
- Provider Registry 不保存明文 Secret，不复制 Provider 实现。
- Destination Registry 复用既有 WebhookDestination。
- Export 不改变业务事实，也不得绕过 tenant boundary。
- Operational Audit 必须不可变、可追溯，并记录 actor / action / resource / outcome。
- Canonical Operator Audit 查询必须以 `AuditLog` 为唯一 Operator Action 审计事实源，数据库优化索引必须与该事实源一致。
- 测试 Gate 可以自动探测服务、生成测试上下文并清理测试数据，但禁止自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis 等服务进程。
