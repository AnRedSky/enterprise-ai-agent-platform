# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Durable Scheduler 多实例租约失效恢复与 misfire 边界收敛**。
- 最近完成：**#84 Durable Resume Operator Action 幂等审计收敛**、Scheduler Repository 多实例 lease 并发与 slot 幂等覆盖。

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
- Phase 2.10-II / II-03 Worker / Scheduler Diagnostics 第一切片已实现；
- Phase 2.10-II / II-04 Audit / Trace Correlation Backend 第一切片已实现；
- Phase 2.10-II / II-05 Controlled Batch Operations Backend 第一切片已实现，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-06 Runtime Audit Query Backend 第一切片与 `0050_runtime_audit_query_indexes` 查询性能强化已完成，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-07 Runtime Audit Query 主体、组合过滤及响应契约硬化已完成 Backend 实现；
- Runtime Audit / Trace Correlation 响应 Contract 已从 `list[Any]` 收紧为明确的 Trace / Audit Item 类型，并增加 Trace ID 输入边界；
- Runtime Audit / Trace Correlation 历史审计恢复路径已补齐：正式 `workflow_execution_id` 优先，缺失时通过 tenant-scoped `trace_id` 恢复当前 Workflow Execution，不猜测旧 `execution_id` 映射；
- Runtime Trace Resolution 已补齐重复 Trace Event 与跨 Execution 歧义保护：同一 Execution 的重复 Trace Event 使用唯一 Execution 映射，跨 Execution 的同 Trace ID 返回 409，不通过首行猜测；
- Operator Audit Query Service 已基于 AuditLog 唯一事实源实现 tenant-scoped 分页、精确过滤和时间窗口校验；
- Operator Audit Query API Contract 已实现，响应模型明确为 `OperatorAuditQueryResponse` / `OperatorAuditItem`；
- Operator Audit Query 已增加 admin-only 访问治理；
- `0051_operator_audit_query_indexes` 已将 Canonical Operator Audit 常用 tenant-scoped 查询索引正式落到 `audit_logs`；
- `0055_operator_audit_operator_action_index` 已为直接 Operator Action → AuditLog 查询补充 tenant-scoped 复合索引；
- Runtime Correlation 的 `AuditLogItem` 已暴露既有 `resource_type`、`resource_id`、`request_id`、`trace_id`，使 Execution / Trace / Audit / Operator Action 深链响应能够完整表达已有审计事实；
- II-09 已新增 Retry Operator Action → Idempotency Result Resource → AuditLog → Workflow Execution → Workflow Trace 的真实 PostgreSQL 验收；
- #84 已将 Durable Resume 的底层确定性 Resume Execution 幂等键收敛到 Operator Action Governance，重放直接复用同一 Result Resource，不重复生成 Operator Audit；
- Phase 2.4 Scheduler Repository 已补齐真实 PostgreSQL 多实例 lease 并发唯一 owner、tenant isolation 与 schedule slot 幂等验证；
- Scheduler misfire 规则已补齐 `skip / fire_once / catch_up` 的确定性单元覆盖；
- Scheduler lease 失效恢复已新增真实 PostgreSQL 验收：过期 lease 可由新 owner 抢占，旧 owner 不能释放新 owner 的 lease。

## 3. 最新本地反馈

开发者已反馈最新 main 基线结果：

- Scheduler Misfire / Lease Gate：`5 passed`，并通过 PostgreSQL readiness、misfire `skip / fire_once / catch_up`、lease reclaim 与 stale-owner fencing 验证；
- Scheduler Repository concurrency integration：`3 passed in 0.77s`；
- Scheduler Lease Concurrency Gate：`3 passed in 0.82s`，并确认未执行任何服务生命周期操作；
- Backend default regression：`1044 passed, 4 skipped, 80 deselected in 36.86s`；
- Operator Action Result Lineage Gate：Runtime Correlation Contract、Retry Lineage、Rollback、Resume Lineage 与服务边界均通过；
- Resume Operator Action Acceptance：`1 passed in 1.53s`。

以上结果均来自开发者实际本地执行，不使用 GitHub Actions 作为验收依据。

Scheduler Runtime PostgreSQL Acceptance 首次本地执行发现两类问题：Workflow Definition fixture 缺少 `nodes` 数组，以及 cleanup 漏删 Runtime Integration Event。两项均已修复，但修复后的 Runtime Gate 尚未获得新的开发者本地实际输出，因此暂不标记为通过。

## 4. 当前 Backend 修复 / 开发

- Scheduler Repository 使用单条 PostgreSQL `UPDATE` 原子 claim，租约有效期由 `lease_owner + lease_expires_at` 成对表达；
- 过期 lease 可被新 Scheduler owner 重新抢占；重新抢占后旧 owner 的 release 会因 owner 条件失败，不会清理新 owner 的 lease；
- `schedule_slot_key` 使用 PostgreSQL 唯一约束收敛重复槽位 claim；
- misfire 规划保持在 `workflow_scheduler/misfire.py` 单一正式入口，不在 Runtime 复制算法；
- 新增 `tests/unit/services/workflow_scheduler/test_misfire.py`，锁定时间边界与参数校验；
- 新增 `tests/integration/test_workflow_scheduler_lease_expiry.py`，锁定真实 PostgreSQL lease reclaim / stale-owner fencing；
- 新增 `scripts/test/phase-2.4/21_scheduler_misfire_lease_gate.ps1`，只检查 PostgreSQL readiness 并运行 targeted tests，禁止自动启动或停止 API / Scheduler / Worker / PostgreSQL / Redis；
- 新增 `tests/integration/test_workflow_scheduler_runtime.py` 与 `scripts/test/phase-2.4/22_scheduler_runtime_gate.ps1`，验证 Scheduler Runtime 的 Schedule → Slot → Execution → Frontier → Audit/Trace 持久化闭环；
- 修复 Runtime Acceptance Fixture：显式 flush `WorkflowTrigger` 后再创建 `WorkflowSchedule`，消除无 ORM relationship 时 SQLAlchemy INSERT 顺序不确定导致的 PostgreSQL FK violation；
- 修复 Runtime Acceptance Fixture：WorkflowVersion 使用 `{"nodes": []}`，满足 `WorkflowRuntime.validate_definition()` 的 Definition 输入契约并保留历史空节点兼容路径；
- 修复 Runtime Acceptance Cleanup：删除测试租户前清理 `integration_events`，避免 Runtime Integration Event 的 tenant 外键阻止测试数据回收。

## 5. 下一执行顺序

```text
① 重新执行 Scheduler Runtime Real PostgreSQL Acceptance，确认 Definition 与 cleanup 修复后进入真实 Runtime tick
② 验证 skip / fire_once / catch_up → WorkflowSchedule → ScheduleSlot → WorkflowExecution
③ 验证 Scheduler Audit / Trace / Integration Event 与 tenant/workflow/execution 关联
④ 验证 lease 失败恢复、slot 幂等与 Execution 幂等不重复
⑤ 更新 Phase 2.4 Acceptance 汇总并评估是否达到 Passed
⑥ Backend-first 继续推进 Operator Governance / Runtime 剩余真实业务缺口
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
