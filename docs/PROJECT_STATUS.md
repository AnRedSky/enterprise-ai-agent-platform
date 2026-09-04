# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Operator Governance 幂等并发、租户隔离、事务结果事实一致性与 Canonical Audit 查询路径收敛**。
- 最近完成：**Scheduler Runtime Real API 最终验收**、Scheduled Trigger 多实例/恢复验收、#84 Durable Resume Operator Action 幂等审计收敛、Operator Governance 最终化 rollback 保护、AsyncMock warning 根因修复、Operator Action API Contract 13 项验收、Trigger Lifecycle PostgreSQL Acceptance、Execution run/cancel 治理事务 Acceptance、Retry/Resume 跨 Session 并发验收测试、Canonical Operator Audit 查询索引验收。

开发严格基于远端 `main`，不创建功能分支。

## 2. 最新本地验证

开发者最新 Backend default regression：

```text
1062 passed, 21 skipped, 80 deselected in 39.30s
```

执行命令：

```powershell
uv run pytest -q -W error -s
```

本次反馈确认 Windows 环境下 `-W error` 回归通过；跳过项来自显式数据库/Real API 等外部依赖测试，不将未启用依赖的 skip 解释为失败。

Operator Audit Query Governance Gate 最新开发者反馈：

```text
39 passed, 905 deselected in 2.86s
3 passed in 0.37s
Gate completed successfully
```

该反馈证明原 Gate 的 unit/API regression、migration/head verification、既有 PostgreSQL Acceptance 与服务启动边界均通过；但原 Gate 尚未执行后来新增的 Retry/Resume 跨 Session 并发测试，也没有真正验证查询计划使用 Canonical 索引。本轮已修复 Gate 覆盖漂移，新增验收结果必须重新由开发者本地执行确认。

对应 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\26_operator_audit_query_performance_gate.ps1
```

Gate 现在额外执行：

```text
Operator Action Idempotency PostgreSQL Acceptance
Retry / Resume cross-session concurrency Acceptance
Canonical Operator Audit query-plan performance Acceptance
```

Alembic：

```powershell
uv run alembic upgrade head
```

Gate 在 PostgreSQL acceptance 前执行 migration head verification；真实迁移结果以本地执行输出为准。

## 3. 当前 Backend 开发状态

- Phase 2.7 Advanced Workflow 主线、Durable Workflow / Resume / Frontier / Scheduler 基础设施已完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成对应真实验收；
- Phase 2.9 Event Contract、Durable Event Persistence、Reliable Delivery、Webhook、Runtime Integration 已完成；
- Phase 2.10-A/B/C/D Event、Delivery、Replay、Audit 运维能力已实现；
- Phase 2.10-E Operations Console 第一切片、Metrics/SLO、Dead Letter、Runtime Operational Acceptance 已实现；
- Phase 2.10-I Runtime Notification Lifecycle、Worker tenant/consumer-group Claim isolation、Retry/Dead Letter/Fallback、SLO/Metrics、Canonical Metrics Export、OpenTelemetry SDK Telemetry、Operational Audit 已完成；
- Phase 2.10-II / II-01 Operator Action Governance、II-02 Global Runtime Operations、II-03 Worker/Scheduler Diagnostics、II-04 Audit/Trace Correlation、II-05 Controlled Batch Operations、II-06/II-07 Runtime Audit Query 已完成对应 Backend 能力；
- Operator Audit Query 已具备 tenant-scoped 分页、精确过滤、时间窗口校验和 admin-only 访问治理；
- `0051_operator_audit_query_indexes` 与 `0055_operator_audit_operator_action_index` 已补齐 Canonical Operator Audit 查询索引；
- Retry Operator Action → Idempotency Result Resource → AuditLog → Workflow Execution → Workflow Trace 已具备真实 PostgreSQL 验收基础，并继续补强成功重放、最终化失败原子性及跨 Session 并发收敛；
- Durable Resume 的确定性 Resume Execution 幂等键已收敛到 Operator Action Governance，重放复用同一 Result Resource，不重复生成 Operator Audit；
- Scheduler 多实例 lease、slot 幂等、tenant isolation、misfire 与 lease expiry recovery 已完成真实 PostgreSQL 验收；
- Scheduled Trigger 多 Scheduler Real API Gate 已完成；
- Operator Governance `run / cancel / retry / resume / trigger` 已统一采用治理事务提交边界，最终化失败和最终 commit 失败显式 rollback；
- Trigger `enable / disable / delete` 已完成真实 PostgreSQL 生命周期验收，非法状态不会生成 Operator Audit，最终审计失败会回滚状态；
- Execution `run / cancel` 已补齐真实 PostgreSQL 治理事务验收，验证成功状态与 Operator Audit 同事务提交、非法状态拒绝以及最终审计失败回滚；
- Retry / Resume 已新增真实 PostgreSQL 双 Session 并发验收：两个独立数据库事务同时竞争同一个 Operator Action 时，要求最终仅存在一个 Result Workflow Execution；竞争请求只能 replay 已成功 Result Resource 或返回稳定 409，禁止第二个 Retry / Resume Execution；
- AsyncMock warning 根因已修复，Backend default regression 在 `-W error` 下通过；
- Operator Action HTTP Contract 已覆盖认证、请求默认值、Idempotency-Key 转发及 409 冲突映射；
- 本轮发现并修复 `26_operator_audit_query_performance_gate.ps1` 的测试覆盖漂移，并新增 Canonical Audit 查询计划验收。

## 4. 当前新增实现

`backend/tests/integration/test_operator_action_idempotency.py` 使用真实 PostgreSQL 验证：

1. 同一 tenant、同一 Idempotency-Key 的两个独立数据库事务并发 claim 只有一个 winner；
2. loser 能读取已提交的 started 幂等事实，而不会创建第二条记录；
3. 相同 Idempotency-Key 在不同 tenant 可以独立 claim；
4. 相同 tenant 的 Idempotency-Key 跨 resource 复用返回 409；
5. failed Idempotency Record 不能被当作成功结果复用；
6. Retry 成功后重复使用同一 key 会复用同一 Result Resource，不创建第二个 Retry Execution，也不重复生成 Operator Audit；
7. Retry 治理最终 Audit 失败时，Result Resource、OperatorActionIdempotency、Workflow Audit/Trace 在同一数据库事务中全部回滚；
8. 所有测试 Tenant/User/Workflow/WorkflowVersion/Execution/Idempotency 数据均由测试自动生成并在 `finally` 中清理。

`backend/tests/integration/test_operator_trigger_invoke.py` 已覆盖：

1. Trigger Invoke 成功重放复用同一 Execution；
2. 同 key 并发 Invoke 收敛到单一 Execution 与 Audit；
3. 不可用 Trigger 的新 key 不残留 transient Idempotency Record；
4. Trigger 状态变化后成功 key 仍可重放原结果；
5. Invoke 最终化失败时 Execution、Idempotency、Audit、Trace、Integration Event 一致回滚。

`backend/tests/integration/test_operator_trigger_lifecycle_governance.py` 已覆盖：

1. Enable / Disable 状态持久化及 Operator Audit；
2. 非法重复 Enable/Disable 返回 409 且不产生 Audit；
3. Delete 与 Operator Audit 原子提交；
4. 最终 Audit 失败时 Trigger 状态、Audit、Idempotency 全部回滚。

`backend/tests/integration/test_operator_execution_governance.py` 新增真实 PostgreSQL 治理验收：

1. Run 成功时 Execution 状态与 Operator Audit 同事务持久化；
2. Cancel 成功时 Execution 状态与 Operator Audit 同事务持久化；
3. 非法 Execution 状态返回 409 且不生成 Operator Audit；
4. Run 最终 Audit 失败时 Execution 状态、Audit、Idempotency 全部回滚。

`backend/tests/integration/test_operator_execution_retry_resume_concurrency.py` 新增跨 Session 并发验收：

1. Retry：两个独立 `AsyncSession` 同时提交同一个 `Idempotency-Key`，最终只能存在一个 `retry_of_execution_id = 原 Execution` 的 Result Workflow Execution；
2. Retry：竞争请求只能获得同一 Result Resource 的 replay，或在竞争边界返回 409，不允许产生第二个 Retry Execution；
3. Retry：最终 `OperatorActionIdempotency.result_resource_id` 必须指向唯一 Retry Execution，且对应 Operator Audit 只能存在一条；
4. Resume：两个独立 `AsyncSession` 同时竞争同一个确定性 `resume:{execution_id}:checkpoint:{sequence}`，最终只能存在一个 Resume Execution；
5. Resume：Result Resource、Resume Checkpoint Sequence、Execution idempotency key 与 Operator Action 幂等事实必须一致，Operator Audit 不得重复；
6. 测试只使用真实 PostgreSQL ORM/领域服务链路，不启动 API、Worker、Scheduler，也不要求人工输入测试数据。

`backend/tests/api_real/test_operator_audit_query_performance_acceptance.py` 新增查询计划验收：

1. action 过滤命中 `ix_operator_audit_tenant_action_created`；
2. actor 过滤命中 `ix_operator_audit_tenant_actor_created`；
3. resource 过滤命中 `ix_operator_audit_tenant_resource_created`；
4. workflow execution 过滤命中 `ix_operator_audit_tenant_execution_created`；
5. trace 过滤命中 `ix_operator_audit_tenant_trace_created`；
6. operator action 过滤命中 `ix_operator_audit_tenant_operator_action_created`；
7. 通过 PostgreSQL `EXPLAIN` 验证 Canonical tenant-first 索引可用，不写入业务测试数据。

`backend/scripts/test/phase-2.10/26_operator_audit_query_performance_gate.ps1` 现作为扩展后的 Operator Audit Governance Gate，顺序为：

```text
PostgreSQL dependency / migration head
    ↓
Operator Governance unit/API regression
    ↓
Operator Action Idempotency / Trigger / Execution / Retry / Resume PostgreSQL Acceptance
    ↓
Canonical Operator Audit query-plan performance Acceptance
    ↓
Service startup boundary
```

脚本只探测依赖并执行测试，不自动启动、停止或重启任何受保护服务；测试数据由测试自动生成与清理，不要求手工填写 ID、Token 或修改源码。

## 5. 下一执行顺序

```text
① 开发者本地重新执行扩展后的 26 Operator Audit Governance Gate
② 若 Gate 暴露问题，只修复 canonical Operator Governance / Audit 查询路径，不创建兼容垫片或第二实现
③ Backend Regression + Alembic head verification
④ 执行 25 Operator Action Result Lineage Gate，确认 partial-commit 反向验收与最新 main 一致
⑤ 评估 Phase 2.10-II Backend Release Gate
⑥ 继续处理剩余 Worker / Delegation 多实例真实 Provider 缺口
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
