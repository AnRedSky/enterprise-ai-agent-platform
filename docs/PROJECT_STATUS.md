# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Operator Action 事务边界与结果事实一致性收敛**。
- 最近完成：**Scheduler Runtime Real API 最终验收**、Scheduled Trigger 多实例/恢复验收、#84 Durable Resume Operator Action 幂等审计收敛。

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
- Scheduler lease 失效恢复已新增真实 PostgreSQL 验收：过期 lease 可由新 owner 抢占，旧 owner 不能释放新 owner 的 lease；
- Scheduler Runtime Real PostgreSQL Acceptance 已通过：Schedule → Slot → Execution → Frontier → Audit/Trace 持久化闭环、due candidate dirty-data 边界及 targeted regression 均通过；
- Scheduled Trigger Real API Gate 已通过：3 个真实 HTTP 场景覆盖 Trigger 生命周期、双 Scheduler 收敛、历史 recovery slot 与 Execution 元数据，最终 `3 passed in 8.79s`。

## 3. 最新本地反馈

开发者最新 Backend Regression Gate：

```text
Backend regression: 1051 passed, 7 skipped, 80 deselected in 38.22s
Database migration/head: 0056_merge_legacy_audit_and_operator_governance_heads (head)
Tenant-safe Real HTTP API: 75 passed, 1 skipped, 2 deselected, 3 failed in 90.63s
```

Real API 三个失败均集中在 Phase 2.8 Delegation Real API：

1. B4 timeout fixture 在真实多 Worker 环境下调用 `claim_delegation()` 时，后台 Worker 已先将 Delegation 认领为 `running`；
2. B2 bridge 在 Delegation 已正常完成后才调用仅允许 `running` 的 `AgentDelegationRuntimeBridge.load()`，属于测试观察窗口错误；
3. B6 multi-worker 至少一个 Delegation 最终为 `failed`，错误为 `Mock provider HTTP 503`。该项尚未放宽为允许 `failed`，必须继续定位 Provider/Runtime 装配原因。

本轮已修复：

- `claim_delegation()` 增加显式 `commit` 事务边界，默认保持原有行为，`commit=False` 时只 flush；
- B4 timeout 使用 `commit=False`，将 Claim、Worker Execution、Frontier 与 `timeout_at` 放入同一事务，消除提交前的后台 Worker 竞争窗口；
- B2 Fixture 将 Mock Profile 与 Claim 放入同一事务，避免 Profile 尚未装配时被真实 Worker 抢占，并停止在 Delegation 已终态后调用 running-only Bridge；
- 上述并发 Fixture 根因与 B6 未决 Provider 503 已记录在 `docs/04-errors/2026-09-03-delegation-real-api-concurrency-fixture.md`。

当前用户本地 `HEAD` 为 `d21f772...` 时，远端 `main` 已继续前进到 `14dc3e2...`；其中 `14dc3e2` 仅包含 Runtime Correlation 前端回归相关变更。后续本地测试应先同步最新 `main`，再验证本轮 Backend 修复。

## 4. 当前 Backend 修复 / 开发

- Scheduler Repository 使用单条 PostgreSQL `UPDATE` 原子 claim，租约有效期由 `lease_owner + lease_expires_at` 成对表达；
- 过期 lease 可被新 Scheduler owner 重新抢占；重新抢占后旧 owner 的 release 会因 owner 条件失败，不会清理新 owner 的 lease；
- `schedule_slot_key` 使用 PostgreSQL 唯一约束收敛重复槽位 claim；
- misfire 规划保持在 `workflow_scheduler/misfire.py` 单一正式入口，不在 Runtime 复制算法；
- Scheduled Trigger 只允许调用正式 published Workflow Definition，禁止通过 legacy empty-node 兼容参数绕过发布契约；
- Trigger Service 的 Manual Invoke 现在提供显式 `commit` 事务边界，Operator Governance 可以把 Execution、Trigger Audit、Operator Action Idempotency 与最终治理 Audit 放入同一提交边界；
- Operator Action API Contract 已补充 Manual Trigger deferred-commit 边界测试；
- Retry / Resume 已保持 `commit=False` → Result Resource / Operator Action / Audit / Trace → 单次提交的治理路径；
- Delegation Claim 现在同样提供显式 `commit` 边界，支持真实 Worker Fixture 在同一事务中完成 Claim + Execution + Frontier 装配；
- 当前继续检查 Operator Action 的 `run / cancel / retry / resume / trigger invoke` 在异常路径下是否留下 partial commit，并补齐真实 PostgreSQL 回滚验收；
- 同时继续定位 B6 multi-worker 的 `Mock provider HTTP 503`，重点检查 target Agent Version → Model Profile → Model Provider → Worker Runtime 的实际装配事实；
- Worker / Scheduler 多实例语义保持不变，不通过降低锁粒度或移除 fencing 来“修复”测试。

## 5. 下一执行顺序

```text
① 同步远端 main 后执行 Delegation B2/B4/B6 targeted Real API
② 定位并修复 B6 Mock Provider 503（若确认生产代码缺陷则修生产代码并补 Unit/Acceptance）
③ Operator Action run / cancel / retry / resume / trigger invoke 异常路径事务一致性
④ Result Resource / OperatorActionIdempotency / AuditLog / Trace 的 partial-commit 回滚验收
⑤ Idempotency-Key 并发 claim 与失败重试语义收敛
⑥ Operator Governance Real PostgreSQL Acceptance
⑦ Backend Regression + Alembic head verification
⑧ 评估 Phase 2.10-II Backend Release Gate
⑨ 继续处理剩余 Worker / Delegation 多实例真实 Provider 缺口
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