# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Operator Action → Audit → Result Resource → Execution/Trace 治理闭环与数据库事实源对齐**。
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片**、**II-05 Controlled Batch Operations Backend 第一切片**、**II-06 Runtime Audit Query Backend 第一切片与查询性能强化**、**II-07 actor 精确过滤、actor + action、action + outcome 组合过滤硬化与查询响应契约硬化**、**Runtime Audit / Trace Correlation 响应 Contract 与历史审计关联硬化**、**Operator Audit Query Service / API Contract 第一实现**、**Operator Audit 管理员访问治理**、**Canonical Operator Audit 查询索引事实源对齐**、**II-08 Runtime Correlation Audit Fact Visibility Contract 扩展**。

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Phase 2.9-A Event Contract、2.9-B Durable Event Persistence、2.9-C Reliable Delivery、2.9-D Webhook Integration、2.9-E Runtime Integration 已完成对应真实验收；
- Phase 2.10-A/B/C/D Event、Delivery、Replay、Audit 运维能力已实现；
- Phase 2.10-E Operations Console 第一切片已实现；
- Phase 2.10-F Metrics / SLO 已增强到 Event Type + Destination + Provider 维度及确定性告警；
- Phase 2.10-G Dead Letter 已增强到批量 Replay；
- Phase 2.10-H Runtime Operational Acceptance Gate 已实现；
- Phase 2.10-I Runtime Notification Lifecycle、Worker tenant/consumer-group Claim isolation、Retry/Dead Letter/Fallback、SLO/Metrics、Canonical Metrics Export、OpenTelemetry SDK Telemetry、Operational Audit 已完成，并已通过本地实际 Real Gate；
- Phase 2.10-II / II-01 Operator Action Governance 已完成本地验证；
- Phase 2.10-II / II-02 Global Runtime Operations 已完成本地 Backend Unit / Real PostgreSQL 验证；
- Phase 2.10-II / II-03 Worker / Scheduler Diagnostics Backend 第一切片已实现；
- Phase 2.10-II / II-04 Audit / Trace Correlation Backend 第一切片已实现；
- Phase 2.10-II / II-05 Controlled Batch Operations Backend 第一切片已实现，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-06 Runtime Audit Query Backend 第一切片与 `0050_runtime_audit_query_indexes` 查询性能强化已完成，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-07 Runtime Audit Query 主体、组合过滤及响应契约硬化已完成 Backend 实现；
- Runtime Audit / Trace Correlation 响应 Contract 已从 `list[Any]` 收紧为明确的 Trace / Audit Item 类型，并增加 Trace ID 输入边界；
- Runtime Audit / Trace Correlation 历史审计恢复路径已补齐：正式 `workflow_execution_id` 优先，缺失时通过 tenant-scoped `trace_id` 恢复当前 Workflow Execution，不猜测旧 `execution_id` 映射；
- Runtime Trace Resolution 已补齐重复 Trace Event 与跨 Execution 歧义保护：同一 Execution 的重复 Trace Event 使用唯一 Execution 映射，跨 Execution 的同 Trace ID 返回 409，不通过首行猜测；
- Operator Audit Query Service 已基于 AuditLog 唯一事实源实现 tenant-scoped 分页、精确过滤和时间窗口校验；
- Operator Audit Query API Contract 已实现，响应模型明确为 `OperatorAuditQueryResponse` / `OperatorAuditItem`，查询参数包含 page、page_size、action、operator_action_id、resource_type、resource_id、actor_id、status、workflow_execution_id、trace_id、since、until；
- Operator Audit Query 已增加 admin-only 访问治理；
- `0051_operator_audit_query_indexes` 已将 Canonical Operator Audit 常用 tenant-scoped 查询索引正式落到 `audit_logs`；
- `0055_operator_audit_operator_action_index` 已为直接 Operator Action → AuditLog 查询补充 tenant-scoped 复合索引；
- Runtime Correlation 的 `AuditLogItem` 已暴露既有 `resource_type`、`resource_id`、`request_id`、`trace_id`，使 Execution / Trace / Audit / Operator Action 深链响应能够完整表达已有审计事实。

## 3. 最新本地反馈与根因

开发者第一次执行 `26_operator_audit_query_performance_gate.ps1` 时，targeted regression 暴露 `audit_logs.operator_action_id` 缺失；第二次执行时 targeted regression 已通过，但 `uv run alembic upgrade head` 暴露 migration graph 存在两个 head：

```text
0013_remove_legacy_audit_execution_fk (head)
0055_operator_audit_operator_action_index (head)
```

根因不是测试数据或服务启动问题，而是历史 `0013_remove_legacy_audit_execution_fk` 分支从 `0012_execution_event_metadata` 独立产生后，一直没有被后续 Operator Governance merge 收敛。此前 `0054_merge_operator_governance_heads` 只合并了 `0048`、`0051`、`0053` 三条 Operator Governance 分支，`0055` 又继续从 `0054` 向前形成新的 head，因此历史 `0013` 仍然保持为独立 head。

## 4. 当前 Backend 修复

- 为 `0048_operator_action_audit_lineage` 保留 `depends_on = "0049_operator_action_idempotency"`，确保全新数据库按 DDL 依赖顺序执行；
- `0054_merge_operator_governance_heads` 保留原有三分支 merge 语义，不重写已经存在的 revision；
- `0055_operator_audit_operator_action_index` 保留 Canonical Operator Audit 直接关联查询索引；
- **新增 `0056_merge_legacy_audit_and_operator_governance_heads`，以 `0055_operator_audit_operator_action_index` 与 `0013_remove_legacy_audit_execution_fk` 为双父节点，正式收敛历史 AuditLog 分支与当前 Operator Governance 分支；**
- 不修改已有 revision ID，不通过 `stamp`、手工修改 `alembic_version` 或删除历史 migration 绕过图结构；
- Operator Audit Contract 中管理员路径已使用 Service mock 隔离真实数据库，保证 API Contract 不因本地 schema 漂移而误报 Contract 失败；
- `26_operator_audit_query_performance_gate.ps1` 继续严格执行 `uv run alembic upgrade head` 与唯一 head 校验，并保持不自动启动任何服务；
- Runtime Trace Resolution Regression Gate 已补齐重复 Trace 与跨 Execution 歧义验证，并通过开发者本地反馈；
- Runtime Correlation Audit Item Contract 已补齐既有审计资源与 Trace 字段，不新增数据库列。

## 5. 下一执行顺序

```text
① 开发者同步远端 main 最新提交
② 执行 uv run alembic heads，确认仅有 0056_merge_legacy_audit_and_operator_governance_heads
③ 执行 uv run alembic upgrade head
④ 重新执行 Operator Governance / Runtime Correlation Gate
⑤ 确认 Operator Action → Audit → Result Resource PostgreSQL Acceptance
⑥ 扫描 Execution / Trace 端到端治理链仍存在的真实业务缺口
⑦ Backend-first 推进下一项 Operator Governance / Audit 能力
⑧ 前端测试与 Browser E2E 暂不作为当前 Backend 主线阻塞条件
```

## 6. Backend 验收规则

当前后端任务只以以下证据作为开发验收依据：

```text
Backend Unit
  ↓
API Contract
  ↓
必要时 Real PostgreSQL / Real API Acceptance
  ↓
Backend Regression
```

Frontend 页面回归、Frontend Build、Browser E2E 不作为 Backend 主线开发阻塞条件。

所有 Gate 均禁止自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；真实 Acceptance 必须自动生成和清理测试身份与业务数据。
