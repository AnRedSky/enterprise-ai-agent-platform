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

### 2.10-II / II-08 Canonical Operator Audit Query Performance / Fact-Source Alignment

状态：**实现已补齐，等待开发者本地重新执行扩展后的 Gate**。

已完成：
- `0051_operator_audit_query_indexes` 为 Canonical `audit_logs` 增加 tenant-scoped 复合查询索引；
- `0054_merge_operator_governance_heads` 收敛 Operator Governance 历史 migration 多 head；
- `audit_logs.operator_action_id` / `operator_action_idempotencies.result_resource_type` PostgreSQL Acceptance 已覆盖；
- Operator Audit Query 增加 `operator_action_id` 精确过滤，直接定位 Operator Action → AuditLog 治理关联；
- 新增 `0055_operator_audit_operator_action_index`，为 `tenant_id + operator_action_id + created_at` 建立 Canonical AuditLog 查询索引；
- API Contract 与 PostgreSQL Acceptance 已同步覆盖该过滤与索引；
- 修复 Gate 覆盖漂移：将 Operator Action Idempotency 与 Retry / Resume 跨 Session 并发验收纳入 `26_operator_audit_query_performance_gate.ps1`；
- 新增查询计划验收，覆盖 action、actor、resource、execution、trace、operator_action 六条正式查询路径，验证 tenant-first Canonical 索引可被 PostgreSQL 查询计划使用；
- Gate 自动设置 `RUN_DATABASE_INTEGRATION=1`，测试数据仍由测试自动生成与清理，不要求人工填写或修改测试代码。

对应 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\26_operator_audit_query_performance_gate.ps1
```

### 2.10-II / II-09 Operator Action Result Lineage

状态：**实现完成，等待最新代码的开发者本地 Backend Regression / Real PostgreSQL Gate 实际反馈**。

已完成：
- Retry Operator Action 的 `WorkflowExecutionService.retry()` 增加 `*, commit: bool = True`，默认保持直接调用兼容；
- Operator Governance Retry / Resume 均使用 `commit=False`，由 Governance 在 Result Resource、Operator Action、Audit 全部 flush 成功后统一提交；
- 新增最终 Operator Audit 失败的真实 PostgreSQL 回滚验收，验证 Retry Execution、Operator Action Idempotency、Audit 与 Trace 不留下半提交事实；
- Phase 2.10 Result Lineage Gate 已纳入正常链路与事务回滚两条 Real PostgreSQL Acceptance；
- 修复 Real Acceptance 中全局 AsyncEngine 默认连接池跨 pytest function-scoped event loop 复用 asyncpg Connection 的问题，测试改用独立 `NullPool` Engine，保持生产连接池配置不变；
- 保持 tenant boundary、Idempotency-Key 冲突与并发安全语义不变。

对应 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1
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
- `operator_action_id` 是 Operator Action → AuditLog 的正式关联键，查询接口允许管理员按该键直接定位治理事实。
- 测试 Gate 可以自动探测服务、生成测试上下文并清理测试数据，但禁止自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis 等服务进程。
